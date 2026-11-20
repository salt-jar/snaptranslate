# -*- coding: utf-8 -*-
"""离线翻译语言包的下载与管理。

设计要点
--------
**为什么不用 argostranslate 那一整套**

离线翻译的模型文件（`.argosmodel`）本质上就是「CTranslate2 模型目录 +
sentencepiece 分词器」的 zip 包。argostranslate 除了要拉 spacy / stanza /
minisbd 一大串依赖（约 150MB），运行期还会**偷偷联网下载**句子切分模型——
对于「本地安全翻译」这个诉求来说这是不可接受的。

所以这里只依赖 ``ctranslate2`` + ``sentencepiece``（约 44MB），
自己完成「下载 → 解压 → 分词 → 推理 → 解码」，模型下载完之后
**整个过程不再产生任何网络请求**。

**为什么要有多个下载源**

``raw.githubusercontent.com`` 在国内极不稳定（实测时好时坏，经常超时/502），
而 jsDelivr 的 CDN 稳定且快（实测 327ms）。因此索引默认走 jsDelivr，
并保留多个备用镜像轮流重试。语言包本体由 ``argos-net.com`` 提供，
支持断点续传。
"""
from __future__ import annotations

import json
import shutil
import ssl
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import paths

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
_SSL = ssl.create_default_context()

#: 索引镜像，按「实测速度」排序。jsDelivr 的 CDN 在国内最快最稳。
INDEX_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/argosopentech/argospm-index@main/index.json",
    "https://gcore.jsdelivr.net/gh/argosopentech/argospm-index@main/index.json",
    "https://fastly.jsdelivr.net/gh/argosopentech/argospm-index@main/index.json",
    "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json",
    "https://ghproxy.net/https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json",
]

INDEX_TTL = 24 * 3600          # 索引缓存有效期（秒）


class OfflineError(RuntimeError):
    """可以直接展示给用户的错误。"""


@dataclass
class PackInfo:
    from_code: str
    to_code: str
    from_name: str
    to_name: str
    version: str
    url: str

    @property
    def pair(self) -> Tuple[str, str]:
        return (self.from_code, self.to_code)

    @property
    def pair_label(self) -> str:
        return "%s → %s" % (self.from_name or self.from_code,
                            self.to_name or self.to_code)

    @property
    def folder(self) -> str:
        return "%s_%s" % (self.from_code, self.to_code)


@dataclass
class PackState:
    """某个语言包在本机的状态。"""

    info: Optional[PackInfo] = None
    installed: bool = False
    path: Optional[Path] = None
    size_mb: float = 0.0
    broken: bool = False
    note: str = ""
    languages: List[str] = field(default_factory=list)


# --------------------------------------------------------------------- 路径


def models_root() -> Path:
    """语言包根目录。优先放程序目录（绿色便携），不可写时退回配置目录。"""
    root = paths.app_dir() / "models" / "offline"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write_test"
        probe.write_text("1", encoding="utf-8")
        probe.unlink()
        return root
    except Exception:
        d = paths.config_dir() / "models" / "offline"
        d.mkdir(parents=True, exist_ok=True)
        return d


def pack_dir(from_code: str, to_code: str) -> Path:
    return models_root() / ("%s_%s" % (from_code, to_code))


def _index_cache() -> Path:
    return paths.cache_dir() / "argos_index.json"


def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return r.read()


# --------------------------------------------------------------------- 索引


def fetch_index(force: bool = False, retries: int = 2) -> List[PackInfo]:
    """获取语言包索引；带本地缓存与多镜像重试。"""
    cache = _index_cache()
    if not force and cache.exists():
        try:
            age = time.time() - cache.stat().st_mtime
            if age < INDEX_TTL:
                data = json.loads(cache.read_text(encoding="utf-8"))
                return _parse_index(data)
        except Exception:
            pass

    last_err: Optional[str] = None
    for mirror in INDEX_MIRRORS:
        for attempt in range(retries):
            try:
                raw = _http_get(mirror, timeout=25)
                data = json.loads(raw.decode("utf-8"))
                packs = _parse_index(data)
                if not packs:
                    raise OfflineError("索引内容为空")
                try:
                    cache.write_bytes(raw)
                except Exception:
                    pass
                return packs
            except Exception as e:  # noqa: BLE001
                last_err = "%s（%s）" % (type(e).__name__, str(e)[:80])
                time.sleep(0.7 * (attempt + 1))

    # 全部失败但本地有旧缓存就先用着
    if cache.exists():
        try:
            return _parse_index(json.loads(cache.read_text(encoding="utf-8")))
        except Exception:
            pass
    raise OfflineError(
        "无法获取语言包列表（已尝试 %d 个镜像）。\n最后一次错误：%s\n"
        "请检查网络，或稍后重试。" % (len(INDEX_MIRRORS), last_err or "未知")
    )


def _parse_index(data) -> List[PackInfo]:
    out: List[PackInfo] = []
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        links = item.get("links") or []
        if not links:
            continue
        out.append(PackInfo(
            from_code=str(item.get("from_code") or ""),
            to_code=str(item.get("to_code") or ""),
            from_name=str(item.get("from_name") or item.get("from_code") or ""),
            to_name=str(item.get("to_name") or item.get("to_code") or ""),
            version=str(item.get("package_version") or "?"),
            url=str(links[0]),
        ))
    return out


# --------------------------------------------------------------------- 已安装


def installed_pairs() -> Dict[Tuple[str, str], Path]:
    """扫描本机已安装的语言包。"""
    out: Dict[Tuple[str, str], Path] = {}
    root = models_root()
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or "_" not in d.name:
            continue
        model = d / "model"
        spm = d / "sentencepiece.model"
        if not (model / "model.bin").is_file():
            continue
        if not spm.is_file():
            continue
        a, _, b = d.name.partition("_")
        out[(a, b)] = d
    return out


def dir_size_mb(path: Path) -> float:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except Exception:
        pass
    return total / 1048576


# --------------------------------------------------------------------- 下载


def install_pack(info: PackInfo,
                 progress: Optional[Callable[[int, str], None]] = None,
                 cancelled: Optional[Callable[[], bool]] = None) -> Path:
    """下载并安装一个语言包，返回安装目录。

    ``progress(百分比, 说明)`` 用于界面反馈；``cancelled()`` 返回 True 时中断。
    """
    def report(pct: int, note: str) -> None:
        if progress:
            progress(pct, note)

    target = pack_dir(info.from_code, info.to_code)
    if target.exists():
        report(100, "已安装")
        return target

    tmp_zip = models_root() / (".%s.argosmodel.part" % info.folder)
    tmp_dir = models_root() / (".%s.unpack" % info.folder)
    models_root().mkdir(parents=True, exist_ok=True)

    try:
        # ---- 下载（支持断点续传）----
        existing = tmp_zip.stat().st_size if tmp_zip.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if existing:
            headers["Range"] = "bytes=%d-" % existing
        req = urllib.request.Request(info.url, headers=headers)
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
            if r.status == 206:
                total = existing + int(r.headers.get("Content-Length") or 0)
                mode = "ab"
            else:
                existing, total, mode = 0, int(r.headers.get("Content-Length") or 0), "wb"
            got = existing
            last_pct = -1
            with open(tmp_zip, mode) as fh:
                while True:
                    if cancelled and cancelled():
                        raise OfflineError("已取消")
                    chunk = r.read(262144)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
                    pct = int(got * 100 / total) if total else 0
                    if pct != last_pct:
                        last_pct = pct
                        report(max(1, min(85, pct * 85 // 100)),
                               "下载中 %.1f / %.1f MB" % (got / 1048576, total / 1048576))

        # ---- 解压 ----
        report(88, "解压中…")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_zip) as z:
            z.extractall(tmp_dir)

        # .argosmodel 里通常还有一层 translate-xx_yy-1_9/ 目录，拍平它
        inner = tmp_dir
        for _ in range(3):
            entries = [p for p in inner.iterdir()]
            dirs = [p for p in entries if p.is_dir()]
            files = [p for p in entries if p.is_file()]
            if len(dirs) == 1 and not files:
                inner = dirs[0]
            else:
                break

        if not (inner / "model" / "model.bin").is_file():
            raise OfflineError("语言包内容不完整（缺少 model/model.bin）")
        if not (inner / "sentencepiece.model").is_file():
            raise OfflineError("语言包内容不完整（缺少 sentencepiece.model）")

        report(94, "安装中…")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.move(str(inner), str(target))

        report(100, "完成")
        return target

    finally:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def remove_pack(from_code: str, to_code: str) -> bool:
    d = pack_dir(from_code, to_code)
    if not d.exists():
        return False
    shutil.rmtree(d, ignore_errors=True)
    from .translate import local as local_mod

    local_mod.unload_all()
    return not d.exists()


# --------------------------------------------------------------------- 语言


def lang_name(code: str) -> str:
    """Argos 语言代码 -> 中文名（与主语言表共用同一套名称）。"""
    from .langs import label, normalize_code

    return label(normalize_code(code))


def available_languages(packs: List[PackInfo]) -> List[str]:
    langs = set()
    for p in packs:
        langs.add(p.from_code)
        langs.add(p.to_code)
    return sorted(langs, key=lambda c: (0 if c in ("zh", "en") else 1, lang_name(c)))
