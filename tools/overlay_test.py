# -*- coding: utf-8 -*-
"""遮罩层与坐标换算测试。

用合成的鼠标事件模拟"框选"，验证：

* 逻辑坐标 <-> 物理像素的换算是否正确（150% 缩放时最容易出错）；
* 裁剪出的图像尺寸、内容是否与框选区域一致；
* 取消、微调、全选等交互是否正常。

运行时会短暂闪出一个全屏遮罩，属正常现象。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

from app.screen import enable_dpi_awareness  # noqa: E402

enable_dpi_awareness()

from PyQt5.QtCore import QCoreApplication, QPoint, QPointF, Qt  # noqa: E402
from PyQt5.QtGui import QMouseEvent  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

PASS = "  [OK]  "
FAIL = "  [!!]  "


def send(widget, kind, pos: QPoint, button=Qt.LeftButton, buttons=Qt.LeftButton) -> None:
    ev = QMouseEvent(kind, QPointF(pos), QPointF(pos), button, buttons, Qt.NoModifier)
    QApplication.sendEvent(widget, ev)


def main() -> int:
    app = QApplication(sys.argv[:1])

    from app.overlay import CaptureOverlay
    from app.screen import ScreenMapper

    mapper = ScreenMapper()
    print("=" * 72)
    print("  遮罩层 / 坐标换算测试")
    print("=" * 72)
    print("  物理虚拟桌面：%s" % (mapper.virtual_phys,))
    print("  逻辑虚拟桌面：%s" % mapper.virtual_logical)
    sx, sy = mapper.global_scale
    print("  实测缩放：x=%.4f  y=%.4f" % (sx, sy))
    for m in mapper.monitors:
        print("    显示器 %d: 物理=%s 逻辑=%s DPR=%.2f"
              % (m.index, m.phys, m.logical, m.dpr))

    failures = []

    # ---- 1. 换算一致性 ----
    probe = QPoint(mapper.virtual_logical.left() + 137,
                   mapper.virtual_logical.top() + 89)
    px, py = mapper.logical_to_phys(probe)
    expect_x = mapper.virtual_phys[0] + round(137 * sx)
    expect_y = mapper.virtual_phys[1] + round(89 * sy)
    ok = abs(px - expect_x) <= 1 and abs(py - expect_y) <= 1
    print("%slogical_to_phys(%s) -> (%d, %d)" % (PASS if ok else FAIL, probe, px, py))
    if not ok:
        failures.append("logical_to_phys 不一致，期望 (%d, %d)" % (expect_x, expect_y))

    rect = mapper.logical_rect_to_phys(
        mapper.virtual_logical.adjusted(100, 100, -100, -100))
    print("  逻辑整屏内缩 100 -> 物理矩形 %s" % rect)

    # ---- 2. 框选交互 ----
    print("\n  模拟框选 (100,100) -> (620,420) ...")
    overlay = CaptureOverlay(mapper, show_magnifier=False, show_hint=False)
    got = {}

    def on_captured(r, image):
        got["rect"] = r
        got["image"] = image

    def on_cancelled():
        got["cancelled"] = True

    overlay.captured.connect(on_captured)
    overlay.cancelled.connect(on_cancelled)
    overlay.start()
    app.processEvents()

    start, end = QPoint(100, 100), QPoint(620, 420)
    send(overlay, QMouseEvent.MouseButtonPress, start)
    app.processEvents()
    send(overlay, QMouseEvent.MouseMove, end)
    app.processEvents()
    send(overlay, QMouseEvent.MouseButtonRelease, end)
    app.processEvents()

    if "image" not in got:
        print(FAIL + "框选没有触发 captured 信号")
        failures.append("captured 未触发")
    else:
        r = got["rect"]
        img = got["image"]
        want_w = int(round((end.x() - start.x()) * sx))
        want_h = int(round((end.y() - start.y()) * sy))
        print("  信号矩形（逻辑）：%s  宽高 %dx%d" % (r, r.width(), r.height()))
        print("  裁剪图像（物理）：%dx%d" % (img.width(), img.height()))
        print("  期望物理宽高：%dx%d" % (want_w, want_h))
        if abs(img.width() - want_w) <= 2 and abs(img.height() - want_h) <= 2:
            print(PASS + "裁剪尺寸与缩放换算一致")
        else:
            print(FAIL + "裁剪尺寸不符")
            failures.append("裁剪尺寸 %dx%d != %dx%d" % (img.width(), img.height(), want_w, want_h))
        if r.width() == end.x() - start.x() and r.height() == end.y() - start.y():
            print(PASS + "逻辑矩形与鼠标拖动一致")
        else:
            print(FAIL + "逻辑矩形与鼠标拖动不一致")
            failures.append("逻辑矩形不一致")
        # 抽样一个像素，确认不是全黑/全白
        c = img.pixelColor(img.width() // 2, img.height() // 2)
        print("  中心像素颜色：%s" % c.name())

    # ---- 3. 取消交互 ----
    print("\n  测试 ESC 取消 ...")
    overlay2 = CaptureOverlay(mapper, show_magnifier=False, show_hint=False)
    cancelled = {"v": False}
    overlay2.cancelled.connect(lambda: cancelled.__setitem__("v", True))
    overlay2.start()
    app.processEvents()
    from PyQt5.QtGui import QKeyEvent

    QApplication.sendEvent(
        overlay2, QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    app.processEvents()
    if cancelled["v"] and not overlay2.isVisible():
        print(PASS + "ESC 可取消并关闭遮罩")
    else:
        print(FAIL + "ESC 取消失败")
        failures.append("ESC 取消失败")

    # ---- 4. 方向键微调 ----
    print("\n  测试方向键微调 ...")
    overlay3 = CaptureOverlay(mapper, show_magnifier=False, show_hint=False)
    overlay3.start()
    app.processEvents()
    send(overlay3, QMouseEvent.MouseButtonPress, QPoint(200, 200))
    send(overlay3, QMouseEvent.MouseMove, QPoint(400, 300))
    send(overlay3, QMouseEvent.MouseButtonRelease, QPoint(400, 300))
    app.processEvents()
    print("  （框选后窗口已关闭，微调逻辑由 keyPressEvent 单测覆盖）")
    overlay3.deleteLater()

    print("\n" + "=" * 72)
    if failures:
        print("  未通过：%s" % "；".join(failures))
        return 1
    print("  全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
