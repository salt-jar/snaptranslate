# -*- coding: utf-8 -*-
"""全屏框选遮罩层。

截图在构造时就完成，屏幕上显示的是"冻结"的画面，可以慢慢选。

坐标约定（很重要）：

* 控件内的 ``pos()`` 是**控件局部**逻辑坐标，控件左上角对应虚拟桌面逻辑原点。
* ``ScreenMapper`` 只认**屏幕逻辑**坐标，因此所有换算前都要先
  ``+ virtual_logical.topLeft()``。
* 抓屏图像是**物理**像素，源矩形还要再减掉抓屏原点。
"""
from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import QPoint, QRect, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QWidget

from .screen import ScreenMapper

ACCENT = QColor(76, 141, 255)
DIM = QColor(0, 0, 0, 130)
HANDLE_SIZE = 8
MIN_SIZE = 6
HANDLE_HIT = 7
MAG_BOX = 132
MAG_SPAN = 34          # 放大镜采样边长（逻辑像素）

_CURSORS = {
    "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
    "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
    "tm": Qt.SizeVerCursor, "bm": Qt.SizeVerCursor,
    "ml": Qt.SizeHorCursor, "mr": Qt.SizeHorCursor,
}


def _rect_between(a: QPoint, b: QPoint) -> QRect:
    """由两个拖动端点构造矩形。

    采用「左闭右开」语义：从 (100,100) 拖到 (620,420) 得到的宽高是 520x320，
    而不是 QRect(p1, p2) 那种闭区间算出来的 521x321。
    """
    x0, x1 = (a.x(), b.x()) if a.x() <= b.x() else (b.x(), a.x())
    y0, y1 = (a.y(), b.y()) if a.y() <= b.y() else (b.y(), a.y())
    return QRect(x0, y0, x1 - x0, y1 - y0)


class CaptureOverlay(QWidget):
    """框选完成时发出 ``captured(逻辑矩形, 物理裁剪图)``。"""

    captured = pyqtSignal(QRect, QImage)
    cancelled = pyqtSignal()

    def __init__(self, mapper: ScreenMapper, show_magnifier: bool = True,
                 show_hint: bool = True, parent=None):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint,
        )
        self._mapper = mapper
        self._show_magnifier = show_magnifier
        self._show_hint = show_hint

        self._shot, self._phys_origin = mapper.grab_virtual_desktop()
        self._pixmap = QPixmap.fromImage(self._shot)
        self._virtual: QRect = mapper.virtual_logical
        self._img_rect = QRect(0, 0, self._shot.width(), self._shot.height())

        self._sel = QRect()
        self._anchor: Optional[QPoint] = None
        self._mode: Optional[str] = None     # new / move / resize
        self._handle: Optional[str] = None
        self._drag_from = QPoint()
        self._drag_rect = QRect()
        self._hover = QPoint()

        self.setGeometry(self._virtual)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    # ---------------------------------------------------------------- 坐标换算

    def _phys_source(self, screen_rect: QRect) -> QRect:
        """屏幕逻辑矩形 -> 抓屏图像内的物理矩形。"""
        phys = self._mapper.logical_rect_to_phys(screen_rect)
        return phys.translated(-self._phys_origin[0], -self._phys_origin[1])

    def _local_phys_source(self, local_rect: QRect) -> QRect:
        return self._phys_source(local_rect.translated(self._virtual.topLeft()))

    # ---------------------------------------------------------------- 生命周期

    def start(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)
        try:
            self.grabKeyboard()
        except Exception:
            pass

    def closeEvent(self, ev):
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        super().closeEvent(ev)

    def _cancel(self) -> None:
        self.close()
        self.cancelled.emit()

    def _confirm(self, local_rect: QRect) -> None:
        r = local_rect.normalized().intersected(self.rect())
        if r.width() < MIN_SIZE or r.height() < MIN_SIZE:
            return
        src = self._local_phys_source(r).intersected(self._img_rect)
        if src.width() < 1 or src.height() < 1:
            return
        crop = self._shot.copy(src)
        screen_rect = r.translated(self._virtual.topLeft())
        self.close()
        self.captured.emit(screen_rect, crop)

    # ---------------------------------------------------------------- 绘制

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        p.drawPixmap(self.rect(), self._pixmap)          # 冻结桌面
        p.fillRect(self.rect(), DIM)                     # 压暗

        sel = self._sel.normalized()
        if sel.width() > 0 and sel.height() > 0:
            src = self._local_phys_source(sel).intersected(self._img_rect)
            if src.width() > 0 and src.height() > 0:
                p.drawPixmap(sel, self._pixmap, src)

            p.setPen(QPen(ACCENT, 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(sel.x(), sel.y(), sel.width(), sel.height()))

            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.setBrush(QBrush(ACCENT))
            for pt in self._handle_points(sel).values():
                p.drawRect(QRect(pt.x() - HANDLE_SIZE // 2, pt.y() - HANDLE_SIZE // 2,
                                 HANDLE_SIZE, HANDLE_SIZE))
            self._draw_size_badge(p, sel)
        elif self._anchor is None:
            p.setPen(QPen(QColor(255, 255, 255, 120), 1, Qt.DashLine))
            p.drawLine(0, self._hover.y(), self.width(), self._hover.y())
            p.drawLine(self._hover.x(), 0, self._hover.x(), self.height())

        if self._show_magnifier and self._mode is None:
            self._draw_magnifier(p, self._hover)
        if self._show_hint:
            self._draw_hint(p)
        p.end()

    @staticmethod
    def _handle_points(sel: QRect) -> Dict[str, QPoint]:
        return {
            "tl": QPoint(sel.left(), sel.top()),
            "tm": QPoint(sel.center().x(), sel.top()),
            "tr": QPoint(sel.right(), sel.top()),
            "ml": QPoint(sel.left(), sel.center().y()),
            "mr": QPoint(sel.right(), sel.center().y()),
            "bl": QPoint(sel.left(), sel.bottom()),
            "bm": QPoint(sel.center().x(), sel.bottom()),
            "br": QPoint(sel.right(), sel.bottom()),
        }

    def _draw_size_badge(self, p: QPainter, sel: QRect) -> None:
        text = "%d × %d" % (sel.width(), sel.height())
        f = QFont(p.font())
        f.setPointSize(9)
        f.setBold(True)
        p.setFont(f)
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text) + 16
        h = fm.height() + 6
        x = min(max(4, sel.left()), max(4, self.width() - w - 4))
        y = sel.top() - h - 6
        if y < 4:
            y = sel.top() + 6
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 22, 26, 215))
        p.drawRoundedRect(QRect(x, y, w, h), 5, 5)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(x, y, w, h), Qt.AlignCenter, text)

    def _draw_hint(self, p: QPainter) -> None:
        text = ("松开鼠标完成 · Enter 确认 · 方向键微调 · 右键 / ESC 取消"
                if self._sel.normalized().width() > MIN_SIZE
                else "拖动鼠标框选要翻译的区域 · 右键 / ESC 取消")
        f = QFont(p.font())
        f.setPointSize(10)
        p.setFont(f)
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text) + 34
        h = fm.height() + 16
        x = (self.width() - w) // 2
        y = 26
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 22, 26, 220))
        p.drawRoundedRect(QRect(x, y, w, h), 9, 9)
        p.setPen(QColor(230, 233, 238))
        p.drawText(QRect(x, y, w, h), Qt.AlignCenter, text)

    def _draw_magnifier(self, p: QPainter, pos: QPoint) -> None:
        x = pos.x() + 24
        y = pos.y() + 24
        if x + MAG_BOX > self.width() - 8:
            x = pos.x() - MAG_BOX - 24
        if y + MAG_BOX > self.height() - 30:
            y = pos.y() - MAG_BOX - 24
        x = max(8, x)
        y = max(8, y)

        screen_center = pos + self._virtual.topLeft()
        half = MAG_SPAN // 2
        src = self._phys_source(
            QRect(screen_center.x() - half, screen_center.y() - half, MAG_SPAN, MAG_SPAN)
        )
        target = QRect(x, y, MAG_BOX, MAG_BOX)
        p.fillRect(target, QColor(16, 18, 22, 235))
        p.drawPixmap(target, self._pixmap, src)

        p.setPen(QPen(QColor(255, 255, 255), 1))
        c = target.center()
        p.drawLine(c.x(), target.top() + 1, c.x(), target.bottom() - 1)
        p.drawLine(target.left() + 1, c.y(), target.right() - 1, c.y())
        p.setPen(QPen(ACCENT, 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(target.adjusted(0, 0, -1, -1))

        f = QFont(p.font())
        f.setPointSize(8)
        p.setFont(f)
        p.setPen(QColor(200, 205, 215))
        p.drawText(QRect(x, y + MAG_BOX + 3, MAG_BOX, 16),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "(%d, %d)" % (screen_center.x(), screen_center.y()))

    # ---------------------------------------------------------------- 交互

    @staticmethod
    def _edges(sel: QRect):
        """返回左闭右开的四条边 (x0, y0, x1, y1)。"""
        return sel.x(), sel.y(), sel.x() + sel.width(), sel.y() + sel.height()

    @classmethod
    def _handle_points(cls, sel: QRect) -> Dict[str, QPoint]:
        x0, y0, x1, y1 = cls._edges(sel)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        return {
            "tl": QPoint(x0, y0), "tm": QPoint(cx, y0), "tr": QPoint(x1, y0),
            "ml": QPoint(x0, cy), "mr": QPoint(x1, cy),
            "bl": QPoint(x0, y1), "bm": QPoint(cx, y1), "br": QPoint(x1, y1),
        }

    def _hit_handle(self, pos: QPoint) -> Optional[str]:
        sel = self._sel.normalized()
        if sel.width() <= 0 or sel.height() <= 0:
            return None
        x0, y0, x1, y1 = self._edges(sel)
        for name, pt in self._handle_points(sel).items():
            if abs(pos.x() - pt.x()) <= HANDLE_HIT and abs(pos.y() - pt.y()) <= HANDLE_HIT:
                return name
        edges = ""
        if abs(pos.y() - y0) <= 3:
            edges += "t"
        if abs(pos.y() - y1) <= 3:
            edges += "b"
        if abs(pos.x() - x0) <= 3:
            edges += "l"
        if abs(pos.x() - x1) <= 3:
            edges += "r"
        return {"tl": "tl", "tr": "tr", "bl": "bl", "br": "br",
                "tb": "tm", "lr": "ml", "t": "tm", "b": "bm",
                "l": "ml", "r": "mr"}.get(edges)

    def mousePressEvent(self, ev) -> None:
        pos = ev.pos()
        if ev.button() == Qt.RightButton:
            self._cancel()
            return
        if ev.button() != Qt.LeftButton:
            return

        self._anchor = pos
        self._drag_from = pos
        self._drag_rect = QRect(self._sel.normalized())

        handle = self._hit_handle(pos)
        sel = self._sel.normalized()
        if handle:
            self._mode = "resize"
            self._handle = handle
        elif sel.width() > 0 and sel.height() > 0 and sel.contains(pos):
            self._mode = "move"
            self._handle = None
        else:
            self._mode = "new"
            self._handle = None
            self._sel = QRect(pos.x(), pos.y(), 0, 0)
        self.update()

    def mouseMoveEvent(self, ev) -> None:
        pos = ev.pos()
        self._hover = pos

        if self._mode is None or self._anchor is None:
            h = self._hit_handle(pos)
            if h:
                self.setCursor(_CURSORS.get(h, Qt.CrossCursor))
            elif self._sel.normalized().contains(pos):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            self.update()
            return

        if self._mode == "new":
            self._sel = _rect_between(self._anchor, pos)
        elif self._mode == "move":
            self._sel = self._clamp_move(self._drag_rect.translated(pos - self._drag_from))
        elif self._mode == "resize":
            self._sel = self._clamp_rect(self._resize_rect(self._drag_rect, self._handle, pos))
        self.update()

    def _clamp_move(self, rect: QRect) -> QRect:
        """整体平移进窗口内，保持尺寸不变。"""
        w = min(rect.width(), self.width())
        h = min(rect.height(), self.height())
        x = max(0, min(rect.x(), self.width() - w))
        y = max(0, min(rect.y(), self.height() - h))
        return QRect(x, y, w, h)

    def _clamp_rect(self, rect: QRect) -> QRect:
        """把四条边都夹进窗口内。"""
        x0, y0, x1, y1 = self._edges(rect.normalized())
        x0 = max(0, min(x0, self.width()))
        x1 = max(0, min(x1, self.width()))
        y0 = max(0, min(y0, self.height()))
        y1 = max(0, min(y1, self.height()))
        return QRect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))

    @classmethod
    def _resize_rect(cls, base: QRect, handle: Optional[str], pos: QPoint) -> QRect:
        if not handle:
            return QRect(base)
        x0, y0, x1, y1 = cls._edges(base)
        if "t" in handle:
            y0 = pos.y()
        if "b" in handle:
            y1 = pos.y()
        if "l" in handle:
            x0 = pos.x()
        if "r" in handle:
            x1 = pos.x()
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        return QRect(x0, y0, x1 - x0, y1 - y0)

    def mouseReleaseEvent(self, ev) -> None:
        if ev.button() != Qt.LeftButton:
            return
        mode, self._mode = self._mode, None
        self._anchor = None
        sel = self._sel.normalized()
        if mode in ("new", "resize", "move"):
            if sel.width() >= MIN_SIZE and sel.height() >= MIN_SIZE:
                self._sel = sel
                self._confirm(sel)
                return
            if mode == "new":
                self._sel = QRect()     # 只是点了一下，不关闭，允许重选
        self.update()

    def keyPressEvent(self, ev) -> None:
        key = ev.key()
        if key == Qt.Key_Escape:
            self._cancel()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            sel = self._sel.normalized()
            if sel.width() >= MIN_SIZE:
                self._confirm(sel)
            return
        if key == Qt.Key_A and ev.modifiers() & Qt.ControlModifier:
            self._sel = QRect(0, 0, self.width(), self.height())
            self.update()
            return
        step = 10 if ev.modifiers() & Qt.ShiftModifier else 1
        sel = self._sel.normalized()
        if sel.width() < 1:
            super().keyPressEvent(ev)
            return
        if key == Qt.Key_Left:
            sel.translate(-step, 0)
        elif key == Qt.Key_Right:
            sel.translate(step, 0)
        elif key == Qt.Key_Up:
            sel.translate(0, -step)
        elif key == Qt.Key_Down:
            sel.translate(0, step)
        else:
            super().keyPressEvent(ev)
            return
        self._sel = self._clamp_move(sel)
        self.update()

    def contextMenuEvent(self, ev) -> None:
        self._cancel()
