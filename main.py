# -*- coding: utf-8 -*-
"""截译 SnapTranslate 启动入口。

启动顺序很关键，不要随意调整：

1. 把 ``vendor/`` 加进 ``sys.path``（免安装依赖即可运行）；
2. **导入 OCR 原生扩展**（onnxruntime 等）——必须早于 Qt，否则 DLL 初始化会失败；
3. 声明 DPI 感知并设置 Qt 高 DPI 属性——必须在创建 ``QApplication`` 之前；
4. 创建 ``QApplication``，做单实例检查，最后启动主上下文。

命令行参数::

    python main.py                 # 常驻托盘
    python main.py --capture       # 启动后立刻截图（已运行时则通知原实例截图）
    python main.py --clipboard     # 翻译剪贴板
    python main.py --settings      # 打开设置
    python main.py --quit          # 退出已运行的实例
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

# ---- 关键：先于 Qt 导入原生扩展 ----------------------------------------------
from app.ocr import warmup  # noqa: E402

warmup()

from app.screen import enable_dpi_awareness  # noqa: E402

enable_dpi_awareness()

from PyQt5.QtCore import QCoreApplication, Qt, QTimer  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

log = logging.getLogger("snaptranslate")


def setup_logging() -> None:
    try:
        handler = logging.FileHandler(paths.log_path(), encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    except Exception:
        pass


def install_excepthook(app: QApplication) -> None:
    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("未捕获异常:\n%s", text)
        try:
            QMessageBox.critical(
                None, "截译 · 出错了",
                "程序遇到了一个未处理的错误：\n\n%s: %s\n\n详细信息已写入：\n%s"
                % (exc_type.__name__, exc, paths.log_path()),
            )
        except Exception:
            pass

    sys.excepthook = hook


# --------------------------------------------------------------------- 单实例


def dispatch_external(ctx, command: str) -> None:
    log.info("执行外部命令：%s", command or "(空)")
    if command == "capture":
        ctx.do_capture()
    elif command == "clipboard":
        ctx.do_clipboard()
    elif command == "settings":
        ctx.open_settings()
    elif command == "repeat":
        ctx.do_repeat()
    elif command == "quit":
        ctx.quit()
    else:
        ctx.notify("截译已在运行", "右键托盘图标打开菜单，或直接按快捷键截图翻译")


# --------------------------------------------------------------------- 主流程


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="截译 · 截图翻译")
    parser.add_argument("--capture", action="store_true", help="立即截图翻译")
    parser.add_argument("--clipboard", action="store_true", help="翻译剪贴板内容")
    parser.add_argument("--repeat", action="store_true", help="重译上次区域")
    parser.add_argument("--settings", action="store_true", help="打开设置窗口")
    parser.add_argument("--quit", action="store_true", help="退出正在运行的实例")
    parser.add_argument("--no-single-instance", action="store_true",
                        help="允许多个实例同时运行（调试用）")
    args = parser.parse_args(argv)

    command = ("capture" if args.capture else
               "clipboard" if args.clipboard else
               "repeat" if args.repeat else
               "settings" if args.settings else
               "quit" if args.quit else "show")

    # 单实例：已有实例在跑就把命令交给它（这一步不需要 Qt，所以放在最前面）
    from app.single_instance import forward_command

    if not args.no_single_instance and forward_command(command):
        print("已通知正在运行的截译实例：%s" % command)
        return 0

    setup_logging()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("截译")
    app.setApplicationDisplayName("截译")
    app.setOrganizationName("SnapTranslate")
    app.setQuitOnLastWindowClosed(False)

    from app.config import config
    from app.tray import app_icon

    app.setWindowIcon(app_icon())

    # 依赖缺失时给出人话提示，而不是一堆 traceback
    try:
        import mss  # noqa: F401
    except Exception:
        QMessageBox.critical(
            None, "截译 · 缺少依赖",
            "缺少必要的依赖库（mss）。\n\n"
            "请先双击运行「安装依赖.bat」，或执行：\n    python tools/install_deps.py",
        )
        return 2

    install_excepthook(app)

    from app.app_context import AppContext
    from app.single_instance import SingleInstance

    ctx = AppContext(app, config)
    ctx.apply_theme()
    # 注意要持有引用：SingleInstance 是 QObject，父对象设为 ctx 保证生命周期
    ctx.instance = SingleInstance(lambda cmd: dispatch_external(ctx, cmd), ctx)
    backend = ctx.instance.listen()
    log.info("单实例后端：%s", backend)
    ctx.start()

    original_quit = ctx.quit

    def quit_and_release():
        try:
            ctx.instance.release()
        except Exception:
            pass
        original_quit()

    ctx.quit = quit_and_release       # type: ignore[assignment]
    ctx.tray.quit_app.disconnect()
    ctx.tray.quit_app.connect(quit_and_release)

    from app.translate import set_cache_size

    set_cache_size(int(config.get("behavior.cache_size", 300) or 300))

    first_run = not config.get("behavior.seen_welcome", False)
    if first_run:
        config.set("behavior.seen_welcome", True)

    def after_start() -> None:
        if command == "capture":
            ctx.do_capture()
        elif command == "clipboard":
            ctx.do_clipboard()
        elif command == "repeat":
            ctx.do_repeat()
        elif command == "settings" or first_run:
            ctx.open_settings()

    QTimer.singleShot(400, after_start)

    log.info("启动完成：%s", paths.app_dir())
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
