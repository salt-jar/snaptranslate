# -*- coding: utf-8 -*-
"""环境自检：依次检查依赖、OCR 引擎、翻译引擎，定位问题非常有用。

用法::

    python tools/selftest.py              # 全部检查
    python tools/selftest.py --ocr        # 只测 OCR
    python tools/selftest.py --translate  # 只测翻译
    python tools/selftest.py --image x.png
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

OK = "  [OK]  "
NG = "  [--]  "
BAD = "  [!!]  "


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def check_deps() -> None:
    section("1. 依赖检查")
    mods = [
        ("PyQt5", "图形界面（必需）"), ("mss", "屏幕抓取（必需）"),
        ("numpy", "数值计算（必需）"), ("PIL", "图像处理"),
        ("cv2", "OpenCV，RapidOCR 需要"), ("onnxruntime", "推理引擎，RapidOCR 需要"),
        ("rapidocr_onnxruntime", "离线 OCR 引擎"), ("pyclipper", "RapidOCR 依赖"),
        ("shapely", "RapidOCR 依赖"), ("yaml", "RapidOCR 依赖"),
        ("pynput", "快捷键兜底（可选）"),
    ]
    for mod, desc in mods:
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "")
            print("%s%-24s %-8s %s" % (OK, mod, ver, desc))
        except Exception as e:  # noqa: BLE001
            print("%s%-24s %-8s %s -> %s" % (NG, mod, "", desc, str(e)[:60]))
    print("\n  vendor 目录：%s（%s）" % (paths.vendor_dir(),
                                        "存在" if paths.vendor_dir().is_dir() else "不存在"))
    print("  配置文件：%s" % paths.config_path())


def check_ocr(image: Path) -> None:
    section("2. OCR 引擎")
    # 必须先预热原生扩展，再创建 Qt 应用（否则 onnxruntime 会加载失败）
    from app.ocr import warmup

    warmup()

    from PyQt5.QtGui import QGuiApplication, QImage

    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

    from app.ocr import ENGINES, engine_status

    status = engine_status()
    for e in ENGINES:
        print("  %-14s %-22s %s" % (e.key, e.label, status.get(e.key, "?")))

    if not image.exists():
        from tools.mk_ocr_test_image import main as mk  # type: ignore

        mk()
    img = QImage(str(image))
    if img.isNull():
        print(BAD + "无法读取测试图片：%s" % image)
        return
    print("\n  测试图片：%s  (%dx%d)" % (image.name, img.width(), img.height()))

    for e in ENGINES:
        if not e.available():
            continue
        print("\n  ---- %s ----" % e.label)
        try:
            eng = e({"upscale": 2.0, "enhance": True, "text_score": 0.5,
                     "use_angle_cls": True, "merge_lines": True, "line_tolerance": 0.6})
            t0 = time.perf_counter()
            res = eng.recognize(img)
            dt = (time.perf_counter() - t0) * 1000
            print("  耗时 %.0f ms，识别到 %d 个文本框" % (dt, len(res.boxes)))
            for line in res.text.splitlines():
                print("     | " + line)
        except Exception as ex:  # noqa: BLE001
            print(BAD + "%s: %s" % (type(ex).__name__, str(ex)[:200]))


def check_translate() -> None:
    section("3. 翻译引擎")
    from app.config import config
    from app.translate import FALLBACK_ORDER, list_providers, provider_status

    status = provider_status(config.data)
    for key, label in list_providers():
        if key == "auto":
            continue
        print("  %-18s %-20s %s" % (key, label, status.get(key, "?")))

    sample = "Hello world, this is a screenshot translation test."
    print("\n  测试文本：%s" % sample)
    for key in FALLBACK_ORDER:
        cfg = dict(config.section("translate"))
        try:
            from app.translate import make_provider

            prov = make_provider(key, cfg)
            t0 = time.perf_counter()
            out, detected = prov.translate(sample, "auto", "zh-CHS")
            dt = (time.perf_counter() - t0) * 1000
            print("%s%-18s %5.0fms  检测=%s  →  %s" % (OK, key, dt, detected or "?", out[:80]))
        except Exception as ex:  # noqa: BLE001
            print("%s%-18s %s: %s" % (NG, key, type(ex).__name__, str(ex)[:120]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--translate", action="store_true")
    ap.add_argument("--image", type=Path, default=ROOT / "tools" / "ocr_test.png")
    ap.add_argument("--deps", action="store_true")
    args = ap.parse_args()
    do_all = not (args.ocr or args.translate or args.deps)

    print("截译 SnapTranslate 自检 · Python %s" % sys.version.split()[0])

    # 必须在**任何** Qt 模块被导入之前预热原生扩展。
    # 就连 `import PyQt5.QtCore` 都会让之后的 onnxruntime 加载失败，
    # 而 check_deps 恰好会先导入 PyQt5，所以这里必须先预热。
    from app.ocr import warmup

    warmup()

    if do_all or args.deps:
        check_deps()
    if do_all or args.ocr:
        check_ocr(args.image)
    if do_all or args.translate:
        check_translate()
    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
