# -*- coding: utf-8 -*-
"""端到端冒烟测试：真实启动整个应用（托盘、热键、窗口），
把一张测试图片喂进流水线，验证「识别 → 翻译 → 显示」全链路。

用法::

    python tools/gui_test.py
    python tools/gui_test.py --image tools/ocr_test.png --timeout 60
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

from app.ocr import warmup  # noqa: E402

warmup()

from app.screen import enable_dpi_awareness  # noqa: E402

enable_dpi_awareness()

from PyQt5.QtCore import QCoreApplication, QRect, Qt, QTimer  # noqa: E402
from PyQt5.QtGui import QImage  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, default=ROOT / "tools" / "ocr_test.png")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--shot-dir", type=Path, default=None,
                    help="把结果窗口 / 设置窗口截图保存到该目录，便于人工检查界面")
    args = ap.parse_args()

    if not args.image.exists():
        from tools.mk_ocr_test_image import main as mk  # type: ignore

        mk()

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    from app.app_context import AppContext
    from app.config import config

    print("=" * 70)
    print("  截译 端到端冒烟测试")
    print("=" * 70)
    print("  配置文件：%s" % paths.config_path())

    ctx = AppContext(app, config)
    ctx.apply_theme()
    ctx.start()
    print("  热键注册：%s" % (ctx.hotkey_backend or "未知"))
    if ctx.hotkey_conflicts:
        for action, reason in ctx.hotkey_conflicts.items():
            print("    ! %s：%s" % (action, reason))

    img = QImage(str(args.image))
    if img.isNull():
        print("  [!!] 无法读取测试图片")
        return 2
    print("  测试图片：%s (%dx%d)" % (args.image.name, img.width(), img.height()))

    state = {"done": False, "ok": False, "t0": time.time()}

    def on_finished(_ocr, _tr):
        state["ok"] = True
        state["done"] = True

    def on_failed(stage, msg):
        print("  [!!] %s 阶段失败：%s" % (stage, msg))
        state["done"] = True

    ctx.pipeline.finished.connect(on_finished)
    ctx.pipeline.failed.connect(on_failed)

    def feed():
        print("\n  >>> 模拟框选，开始识别与翻译 ...")
        ctx._on_captured(QRect(100, 100, img.width(), img.height()), img)

    QTimer.singleShot(800, feed)

    deadline = args.timeout
    while not state["done"] and time.time() - state["t0"] < deadline:
        app.processEvents()
        time.sleep(0.03)

    print("\n" + "-" * 70)
    print("  原文：")
    for line in (ctx.result.view_source.toPlainText() or "(空)").splitlines():
        print("    | " + line)
    print("\n  译文：")
    for line in (ctx.result.view_trans.toPlainText() or "(空)").splitlines():
        print("    | " + line)
    print("\n  状态栏：%s" % ctx.result.lbl_status.text())
    print("  窗口可见：%s   尺寸：%dx%d"
          % (ctx.result.isVisible(), ctx.result.width(), ctx.result.height()))
    print("-" * 70)

    ok = state["ok"] and bool(ctx.result.view_trans.toPlainText().strip())

    if args.shot_dir:
        args.shot_dir.mkdir(parents=True, exist_ok=True)
        for _ in range(40):
            app.processEvents()
            time.sleep(0.02)
        shot = args.shot_dir / "result_window.png"
        ctx.result.grab().save(str(shot))
        print("  截图已保存：%s" % shot)

        ctx.open_settings()
        for _ in range(80):
            app.processEvents()
            time.sleep(0.02)
        shot2 = args.shot_dir / "settings_window.png"
        ctx._settings.grab().save(str(shot2))
        print("  截图已保存：%s" % shot2)

        # 再截几张设置页，方便逐页检查
        for idx, name in ((1, "settings_ocr"), (2, "settings_translate"),
                          (3, "settings_ui"), (4, "settings_system")):
            ctx._settings.tabs.setCurrentIndex(idx)
            for _ in range(30):
                app.processEvents()
                time.sleep(0.02)
            ctx._settings.grab().save(str(args.shot_dir / ("%s.png" % name)))
        print("  设置各页截图已保存到：%s" % args.shot_dir)

    print("-" * 70)
    print("  结果：%s" % ("通过 ✓" if ok else "未通过 ✗"))

    ctx.quit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
