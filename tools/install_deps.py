# -*- coding: utf-8 -*-
"""无需 pip 的依赖安装器。

从 PyPI 下载 wheel 并解压到项目的 ``vendor/`` 目录。相比 pip 的好处：

* 不需要 pip / venv 可用（部分 Windows 环境里两者都可能是坏的）；
* 不污染系统 Python 环境，整个程序可以随目录拷贝；
* 只下载必需文件，不做依赖回溯，速度快。

用法::

    python tools/install_deps.py            # 安装缺失的依赖
    python tools/install_deps.py --force    # 全部重装
    python tools/install_deps.py --list     # 只列出状态
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import sysconfig
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor"
WORK = ROOT / ".tmp" / "wheels"
MANIFEST = VENDOR / "_installed.json"

PY_TAG = "cp%d%d" % sys.version_info[:2]
# CPython 3.13 起存在"自由线程(free-threaded)"构建，它的 ABI 标签是 cp313t，
# 与普通 cp313 **不兼容**，必须区分，否则会装错 wheel 导致 ImportError。
FREE_THREADED = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

# (包名, 固定版本或 None, 是否必需, 用途说明)
REQUIREMENTS = [
    ("mss", None, True, "屏幕抓取（多显示器 / 高 DPI）"),
    ("pynput", None, False, "全局快捷键兜底（原生热键被占用时启用）"),
    ("opencv-python-headless", "4.10.0.84", True, "RapidOCR 图像处理（headless 版避免与 Qt 冲突）"),
    ("pyclipper", None, True, "RapidOCR 文本框裁剪"),
    ("shapely", None, True, "RapidOCR 几何运算"),
    ("PyYAML", None, True, "RapidOCR 配置读取"),
    ("rapidocr-onnxruntime", None, True, "离线 OCR 引擎（中英日韩）"),
    # ---- 离线翻译（可选）：只装推理引擎和分词器，语言包在程序里按需下载 ----
    # 不用 argostranslate 那一整套（它还会拉 spacy / stanza / minisbd，
    # 而且运行时会偷偷联网下载句子切分模型，那就不是真离线了）。
    ("ctranslate2", None, False, "离线翻译推理引擎（CTranslate2，CPU 上很快）"),
    ("sentencepiece", None, False, "离线翻译分词器（OPUS-MT 模型配套）"),
]

# 已由系统 Python 提供、无需安装的大包
SYSTEM_PROVIDED = ["onnxruntime", "numpy", "Pillow", "PyQt5"]


def log(msg: str = "") -> None:
    print(msg, flush=True)


def _abi_matches(abi: str) -> bool:
    if abi in ("none", "abi3"):
        return True
    if FREE_THREADED:
        return abi in (PY_TAG, PY_TAG + "t")
    return abi == PY_TAG


def pick_wheel(files, want_version=None):
    """从 PyPI 的 release 文件列表里挑一个最适合当前解释器的 wheel。"""
    best, best_score = None, -1
    for f in files:
        name = f.get("filename", "")
        if not name.endswith(".whl") or f.get("yanked"):
            continue
        parts = name[:-4].split("-")
        if len(parts) < 5:
            continue
        if want_version and parts[1] != want_version:
            continue
        pytag, abi, plat = parts[-3], parts[-2], parts[-1]

        plat_score = 0
        if plat == "win_amd64":
            plat_score = 100
        elif plat == "any":
            plat_score = 10
        else:
            continue

        py_opts = pytag.split(".")
        if not _abi_matches(abi):
            continue
        if PY_TAG in py_opts:
            abi_score = 60 if abi == PY_TAG else 40
        elif "py3" in py_opts or "py2.py3" in py_opts:
            abi_score = 30
        elif abi == "abi3":
            abi_score = 35
        else:
            continue

        score = plat_score + abi_score
        if score > best_score:
            best, best_score = f, score
    return best


def fetch_json(url: str):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "SnapTranslate-Installer/1.0"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url: str, dest: Path, digest: str | None) -> None:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "SnapTranslate-Installer/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r, open(dest, "wb") as fh:
        total = int(r.headers.get("Content-Length") or 0)
        got, last = 0, -1
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            fh.write(chunk)
            got += len(chunk)
            pct = int(got * 100 / total) if total else 0
            if pct != last and pct % 5 == 0:
                last = pct
                print("    %3d%%  %.1f/%.1f MB" % (pct, got / 1048576,
                                                   (total or got) / 1048576), flush=True)
    if digest:
        h = hashlib.sha256()
        with open(dest, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
        if h.hexdigest() != digest:
            dest.unlink(missing_ok=True)
            raise RuntimeError("sha256 校验失败: %s" % dest.name)


def extract_wheel(whl: Path, target: Path) -> None:
    """把 wheel 解压到 target。

    处理 ``*.data/{purelib,platlib,scripts,data}`` 目录，与 pip --target 行为一致。
    """
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(whl) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            name = item.filename
            parts = name.split("/")
            if len(parts) > 2 and parts[1] == "data":
                kind = parts[0].split("-")[0]  # wheel 的 <dist>-<ver>.data
                sub = parts[2]
                if sub in ("purelib", "platlib"):
                    rel = "/".join(parts[3:])
                elif sub == "scripts":
                    rel = "Scripts/" + "/".join(parts[3:])
                else:  # data / headers -> 直接铺到根
                    rel = "/".join(parts[3:])
                del kind
            else:
                rel = name
            if not rel:
                continue
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as src, open(out, "wb") as dst:
                dst.write(src.read())


def installed_versions() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_importable() -> dict:
    """检查关键包能否被 import（在已注入 vendor 的前提下）。"""
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    result = {}
    for mod in ["mss", "pynput", "cv2", "pyclipper", "shapely", "yaml",
                "rapidocr_onnxruntime", "onnxruntime", "numpy", "PIL",
                "ctranslate2", "sentencepiece"]:
        try:
            __import__(mod)
            result[mod] = True
        except Exception as e:  # noqa: BLE001
            result[mod] = "%s: %s" % (type(e).__name__, str(e)[:70])
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="SnapTranslate 依赖安装器（不使用 pip）")
    ap.add_argument("--force", action="store_true", help="忽略已安装记录，全部重新下载")
    ap.add_argument("--list", action="store_true", help="只显示状态")
    args = ap.parse_args()

    logs = sysconfig.get_paths().get("purelib", "")
    log("=" * 68)
    log("  截译 SnapTranslate —— 依赖安装")
    log("=" * 68)
    log("  Python   : %s  (%s)" % (sys.version.split()[0], PY_TAG))
    log("  解释器   : %s" % sys.executable)
    log("  系统库   : %s" % logs)
    log("  安装目标 : %s" % VENDOR)
    log("-" * 68)

    if args.list:
        have = installed_versions()
        for name, ver, need, desc in REQUIREMENTS:
            mark = "已安装" if name.lower() in have else "未安装"
            log("  [%s] %-26s %-10s %s" % ("★" if need else " ", name, mark, desc))
        log("")
        for mod, ok in check_importable().items():
            log("  import %-22s %s" % (mod, "OK" if ok is True else ok))
        return 0

    WORK.mkdir(parents=True, exist_ok=True)
    VENDOR.mkdir(parents=True, exist_ok=True)
    manifest = installed_versions()
    failed = []

    for name, want_ver, required, desc in REQUIREMENTS:
        key = name.lower().replace("_", "-")
        if not args.force and key in manifest:
            log("  ✓ %-26s 已安装 %s" % (name, manifest[key]))
            continue
        log("  ↓ %-26s %s" % (name, desc))
        try:
            data = fetch_json("https://pypi.org/pypi/%s/json" % name)
            version = want_ver or data["info"]["version"]
            files = data["releases"].get(version) or []
            whl = pick_wheel(files, version if want_ver else None)
            if whl is None:
                raise RuntimeError("没有适配 %s / win_amd64 的 wheel" % PY_TAG)
            dest = WORK / whl["filename"]
            if not dest.exists() or dest.stat().st_size != whl["size"]:
                download(whl["url"], dest, (whl.get("digests") or {}).get("sha256"))
            extract_wheel(dest, VENDOR)
            manifest[key] = version
            log("    → %s  %s" % (version, whl["filename"]))
        except Exception as e:  # noqa: BLE001
            log("    ✗ 失败: %s: %s" % (type(e).__name__, e))
            failed.append(name)
            if required:
                pass

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    log("-" * 68)
    log("  导入自检：")
    for mod, ok in check_importable().items():
        log("    %-24s %s" % (mod, "OK" if ok is True else "失败 → " + str(ok)))

    log("-" * 68)
    if failed:
        log("  未完成的包：%s" % ", ".join(failed))
        log("  提示：可重复运行本脚本，或改用  pip install -r requirements.txt")
        return 1
    log("  全部完成。下一步：双击 启动.bat  或运行  python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
