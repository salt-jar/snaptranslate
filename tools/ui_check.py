# -*- coding: utf-8 -*-
"""界面几何自检。

当前无法直接"看"界面时，用几何断言代替肉眼检查：

* 每个可见控件的宽高是否 > 0；
* 是否越出父控件边界（被裁掉的内容用户是看不到的）；
* 结果窗口的文字区域高度是否够显示内容；
* 设置窗口每个标签页是否都能正常布局；
* 导出 PNG 截图供人工复核。

用法::

    python tools/ui_check.py                # 检查并输出报告
    python tools/ui_check.py --shot-dir out # 同时导出截图
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

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
from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402

QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

OK, BAD, WARN = "  [OK]  ", "  [!!]  ", "  [~~]  "


def walk(widget: QWidget) -> List[QWidget]:
    out = [widget]
    for child in widget.findChildren(QWidget):
        out.append(child)
    return out


def audit(root: QWidget, label: str, ignore: Tuple[str, ...] = ()) -> List[str]:
    problems: List[str] = []
    for w in walk(root):
        if not w.isVisible():
            continue
        if w.objectName() in ignore or type(w).__name__ in ignore:
            continue
        r = w.geometry()
        name = "%s(%s)" % (type(w).__name__, w.objectName() or "-")
        if r.width() <= 0 or r.height() <= 0:
            problems.append("%s 尺寸为 0：%dx%d" % (name, r.width(), r.height()))
            continue
        parent = w.parentWidget()
        if parent is not None and parent is not root:
            # 滚动区域的内容控件天生比视口高，这是正常的
            if parent.objectName() == "qt_scrollarea_viewport":
                continue
            pr = parent.rect()
            if not pr.contains(r):
                over = QRect(r).intersected(pr)
                if over.width() < r.width() * 0.6 or over.height() < r.height() * 0.6:
                    problems.append(
                        "%s 越界超过 40%%：自身 %dx%d @ (%d,%d)，父容器 %dx%d"
                        % (name, r.width(), r.height(), r.x(), r.y(),
                           pr.width(), pr.height()))
    return problems


def describe(root: QWidget, label: str, limit: int = 40) -> None:
    kids = [w for w in walk(root) if w.isVisible() and w is not root]
    print("  %s：%d 个可见控件，窗口 %dx%d" % (label, len(kids), root.width(), root.height()))
    shown = 0
    for w in kids:
        if shown >= limit:
            print("    ...")
            break
        r = w.geometry()
        text = ""
        for attr in ("text", "currentText"):
            v = getattr(w, attr, None)
            if callable(v):
                try:
                    text = str(v())[:24]
                    break
                except Exception:
                    pass
        print("    %-22s %4d,%4d %4dx%-4d %s"
              % (type(w).__name__, r.x(), r.y(), r.width(), r.height(), text))
        shown += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, default=ROOT / "tools" / "ocr_test.png")
    ap.add_argument("--shot-dir", type=Path, default=None)
    args = ap.parse_args()

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    from app.app_context import AppContext
    from app.config import config

    print("=" * 74)
    print("  截译 界面几何自检")
    print("=" * 74)

    ctx = AppContext(app, config)
    ctx.apply_theme()

    failures: List[str] = []

    def pump(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    # ---------------- 结果窗口 ----------------
    img = QImage(str(args.image))
    ctx._on_captured(QRect(60, 60, img.width(), img.height()), img)
    for _ in range(600):
        pump(0.05)
        if ctx.result.view_trans.toPlainText().strip():
            break
    pump(0.6)

    print("\n---- 结果窗口 ----")
    describe(ctx.result, "ResultWindow")
    problems = audit(ctx.result, "result")
    for p in problems:
        print(BAD + p)
    failures += problems

    trans = ctx.result.view_trans
    src = ctx.result.view_source
    doc_h = trans.document().size().height()
    print("\n  译文可视高度 %d px，文档高度 %.0f px" % (trans.height(), doc_h))
    if doc_h > trans.height() + 2 and trans.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff:
        msg = "译文被裁切且没有滚动条"
        print(BAD + msg)
        failures.append(msg)
    else:
        print(OK + "译文高度充足或已启用滚动条")
    if src.isVisible() and src.height() < 30:
        msg = "原文区域高度过小：%d" % src.height()
        print(BAD + msg)
        failures.append(msg)

    for btn in ("btn_copy_trans", "btn_copy_both", "btn_speak", "btn_reocr",
                "btn_retry", "btn_pin", "btn_close", "btn_settings"):
        w = getattr(ctx.result, btn, None)
        if w is None or not w.isVisible() or w.width() < 20:
            msg = "按钮 %s 不可见或过小" % btn
            print(BAD + msg)
            failures.append(msg)
    if not failures:
        print(OK + "结果窗口所有关键按钮均可见")

    if args.shot_dir:
        args.shot_dir.mkdir(parents=True, exist_ok=True)
        ctx.result.grab().save(str(args.shot_dir / "result_window.png"))

    # ---------------- 设置窗口 ----------------
    print("\n---- 设置窗口 ----")
    ctx.open_settings()
    pump(1.0)
    dlg = ctx._settings
    tabs = dlg.tabs
    print("  标签页数量：%d  当前：%s" % (tabs.count(), tabs.tabText(tabs.currentIndex())))
    print("  窗口尺寸：%dx%d" % (dlg.width(), dlg.height()))

    for idx in range(tabs.count()):
        tabs.setCurrentIndex(idx)
        pump(0.45)
        name = tabs.tabText(idx)
        page = tabs.widget(idx)
        probs = audit(page, name)
        visible = len([w for w in walk(page) if w.isVisible()])
        flag = OK if not probs else BAD
        print("  %s[%d] %-10s 可见控件 %3d  页面 %dx%d"
              % (flag, idx, name, visible, page.width(), page.height()))
        for p in probs[:6]:
            print("        " + p)
        failures += ["设置页 %s：%s" % (name, p) for p in probs]
        if args.shot_dir:
            dlg.grab().save(str(args.shot_dir / ("settings_%d_%s.png" % (idx, name))))

    # 滚动条是否出现（翻译页内容较长）
    tabs.setCurrentIndex(2)
    pump(0.4)
    scroll = dlg.findChild(type(dlg).__mro__[0], "")  # 占位，避免未使用告警

    # ---------------- 离线语言包窗口 ----------------
    print("\n---- 离线语言包管理 ----")
    try:
        from app.offline_dialog import OfflinePackDialog

        dlg2 = OfflinePackDialog(config, None)
        dlg2.show()
        pump(3.0)          # 等索引拉取（后台线程）
        for _ in range(60):
            pump(0.1)
            if dlg2.table.rowCount() > 0:
                break
        print("  窗口尺寸：%dx%d   表格行数：%d"
              % (dlg2.width(), dlg2.height(), dlg2.table.rowCount()))
        print("  状态栏：%s" % dlg2.lbl_status.text()[:90])
        probs = audit(dlg2, "离线语言包")
        if probs:
            for p in probs[:6]:
                print(BAD + p)
            failures += probs
        else:
            print(OK + "语言包窗口几何检查通过")
        if dlg2.table.rowCount() == 0:
            msg = "语言包列表为空（索引获取失败？）"
            print(WARN + msg)
        if args.shot_dir:
            dlg2.grab().save(str(args.shot_dir / "offline_packs.png"))
        dlg2.close()
    except Exception as e:  # noqa: BLE001
        import traceback

        print(BAD + "离线语言包窗口检查失败：%s" % e)
        print(traceback.format_exc()[-600:])
        failures.append("离线语言包窗口：%s" % e)

    # ---------------- 汇总 ----------------
    print("\n" + "=" * 74)
    if failures:
        print("  发现 %d 个界面问题：" % len(failures))
        for f in failures[:20]:
            print("    · " + f)
        return 1
    print("  界面几何检查全部通过 ✓")
    if args.shot_dir:
        print("  截图已保存到：%s" % args.shot_dir)
    ctx.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
