# -*- coding: utf-8 -*-
"""iOS 风格的自绘控件与无边框卡片窗口。

Qt 自带的控件在 Windows 上即使套上样式表，开关、分段控件、窗口圆角这些
细节仍然很"桌面"。这里用少量自绘把最影响观感的几个部件补上：

* :class:`IOSSwitch` —— 带滑动的系统开关（绿色，和 iOS 设置一致）
* :class:`ActivityIndicator` —— 12 辐条的活动指示器
* :class:`SegmentedTabs` —— 顶部胶囊分段控件 + 内容页
* :class:`FramelessDialog` —— 圆角卡片对话框（自定义标题栏、可拖动）
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QCursor, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme


def colors() -> Dict[str, str]:
    return theme.current_palette()


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


def glyph_button(char: str, tooltip: str = "", size: int = 30,
                 checkable: bool = False) -> QToolButton:
    """Segoe Fluent Icons 的图标按钮（Win10 回退到 Segoe MDL2 Assets）。"""
    btn = QToolButton()
    btn.setText(char)
    btn.setProperty("glyph", True)
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setCheckable(checkable)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def badge_label(text: str = "译", size: int = 24, large: bool = False) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("BadgeLarge" if large else "Badge")
    lab.setFixedSize(size, size)
    lab.setAlignment(Qt.AlignCenter)
    return lab


# --------------------------------------------------------------------------- 开关


class IOSSwitch(QCheckBox):
    """iOS 风格开关。保留 QCheckBox 的 ``isChecked`` / ``setChecked`` 接口。"""

    TRACK_W = 44
    TRACK_H = 26
    KNOB = 22

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._pos = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._animate)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    # ------------------------------------------------------------------ 动画
    def _on_anim(self, value) -> None:
        self._pos = float(value)
        self.update()

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0
        width = self.TRACK_W + (10 + text_w if text_w else 0)
        height = max(self.TRACK_H + 8, fm.height() + 8)
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ------------------------------------------------------------------ 绘制
    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = colors()

        track_on = QColor(c.get("ok", "#34C759"))
        track_off = QColor(c.get("switch_off", "#E9E9EA"))
        track = _mix(track_off, track_on, self._pos)
        if not self.isEnabled():
            track.setAlpha(120)

        top = (self.height() - self.TRACK_H) / 2.0
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, top, self.TRACK_W, self.TRACK_H),
                          self.TRACK_H / 2.0, self.TRACK_H / 2.0)

        knob_x = 2.0 + self._pos * (self.TRACK_W - self.KNOB - 4.0)
        knob_y = top + 2.0
        p.setBrush(QColor(0, 0, 0, 38))
        p.drawEllipse(QRectF(knob_x + 0.4, knob_y + 1.2, self.KNOB, self.KNOB))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(knob_x, knob_y, self.KNOB, self.KNOB))

        if self.text():
            p.setPen(QColor(c.get("text") if self.isEnabled() else c.get("text_dim")))
            rect = QRect(self.TRACK_W + 10, 0, self.width() - self.TRACK_W - 10, self.height())
            p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, self.text())

        if self.hasFocus():
            pen = QPen(QColor(c.get("accent", "#007AFF")))
            pen.setWidthF(1.4)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(-2, top - 2, self.TRACK_W + 4, self.TRACK_H + 4),
                              self.TRACK_H / 2.0 + 2, self.TRACK_H / 2.0 + 2)
        p.end()

    def changeEvent(self, ev) -> None:
        super().changeEvent(ev)
        if ev.type() in (QEvent.StyleChange, QEvent.EnabledChange, QEvent.FontChange):
            self.update()


# --------------------------------------------------------------------------- 加载指示器


class ActivityIndicator(QWidget):
    """iOS 风活动指示器：12 根辐条循环变亮。"""

    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        self._size = size
        self._step = 0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)

    def _tick(self) -> None:
        self._step = (self._step + 1) % 12
        self.update()

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop(self) -> None:
        self._timer.stop()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(self.width() / 2.0, self.height() / 2.0)
        base = QColor(colors().get("text_dim", "#8A8A8E"))
        p.scale(self._size / 16.0, self._size / 16.0)
        for i in range(12):
            p.save()
            p.rotate(i * 30)
            fade = ((i - self._step) % 12) / 11.0
            col = QColor(base)
            col.setAlpha(int(35 + 220 * fade))
            pen = QPen(col)
            pen.setWidthF(1.8)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(0, -7), QPointF(0, -4))
            p.restore()
        p.end()


# --------------------------------------------------------------------------- 分段标签


class SegmentedTabs(QWidget):
    """顶部为 iOS 分段控件、下方为页面堆栈的标签容器。"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons: List[QPushButton] = []
        self._labels: List[str] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._track = QFrame()
        self._track.setObjectName("SegmentedTrack")
        self._track_lay = QHBoxLayout(self._track)
        self._track_lay.setContentsMargins(3, 3, 3, 3)
        self._track_lay.setSpacing(2)
        lay.addWidget(self._track)

        self._stack = QStackedWidget()
        lay.addWidget(self._stack, 1)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

    def addTab(self, widget: QWidget, label: str) -> int:
        index = len(self._buttons)
        btn = QPushButton(label)
        btn.setProperty("segment", True)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setMinimumHeight(28)
        btn.setMinimumWidth(64)
        self._group.addButton(btn, index)
        btn.clicked.connect(lambda _=False, i=index: self.setCurrentIndex(i))
        self._track_lay.addWidget(btn, 1)
        self._buttons.append(btn)
        self._labels.append(label)
        self._stack.addWidget(widget)
        if index == 0:
            self.setCurrentIndex(0)
        else:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        return index

    def count(self) -> int:
        return len(self._buttons)

    def tabText(self, index: int) -> str:
        if 0 <= index < len(self._labels):
            return self._labels[index]
        return ""

    def widget(self, index: int) -> Optional[QWidget]:
        if 0 <= index < self._stack.count():
            return self._stack.widget(index)
        return None

    def currentIndex(self) -> int:
        return self._stack.currentIndex()

    def currentWidget(self) -> Optional[QWidget]:
        return self._stack.currentWidget()

    def setCurrentIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._buttons):
            return
        changed = index != self._stack.currentIndex()
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        if changed:
            self.currentChanged.emit(index)


# --------------------------------------------------------------------------- 无边框卡片对话框


class _DialogHeader(QWidget):
    """对话框标题栏：图标 + 标题 + 关闭按钮，按住可拖动窗口。"""

    def __init__(self, dialog: "FramelessDialog"):
        super().__init__(dialog)
        self._dialog = dialog
        self._offset: Optional[QPoint] = None
        self.setObjectName("DialogHeader")
        self.setFixedHeight(78)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 18, 18, 6)
        lay.setSpacing(12)

        self.icon = badge_label("译", 38, large=True)
        self.icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.icon)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        self.title = QLabel("")
        self.title.setObjectName("TitleLabel")
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("SubtitleLabel")
        self.subtitle.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        lay.addLayout(text)
        lay.addStretch(1)

        self.btn_close = glyph_button("\uE711", "关闭", 30)
        self.btn_close.clicked.connect(dialog.reject)
        lay.addWidget(self.btn_close)

    def set_title(self, title: str, subtitle: str = "") -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.subtitle.setVisible(bool(subtitle))

    # 拖动窗口
    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.LeftButton:
            self._offset = ev.globalPos() - self._dialog.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev) -> None:
        if self._offset is not None and ev.buttons() & Qt.LeftButton:
            self._dialog.move(ev.globalPos() - self._offset)
            ev.accept()

    def mouseReleaseEvent(self, ev) -> None:
        self._offset = None
        ev.accept()


class FramelessDialog(QDialog):
    """圆角卡片对话框：透明外框 + 阴影 + 自定义标题栏。"""

    def __init__(self, parent=None, shadow_margin: int = 18):
        super().__init__(parent)
        self._shadow_margin = shadow_margin
        self._positioned = False
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("CardDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(shadow_margin, shadow_margin, shadow_margin, shadow_margin)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("WindowCard")
        self._shadow = QGraphicsDropShadowEffect(self.card)
        self._shadow.setBlurRadius(48)
        self._shadow.setOffset(0, 12)
        self._shadow.setColor(QColor(0, 0, 0, 120))
        self.card.setGraphicsEffect(self._shadow)
        outer.addWidget(self.card)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)

        self.header = _DialogHeader(self)
        self.card_layout.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(22, 8, 22, 20)
        self.body_layout.setSpacing(14)
        self.card_layout.addWidget(self.body, 1)

        self._refresh_shadow()

    def set_title(self, title: str, subtitle: str = "") -> None:
        self.setWindowTitle(title)
        self.header.set_title(title, subtitle)

    def _refresh_shadow(self) -> None:
        dark = QApplication.instance() is not None and bool(
            QApplication.instance().property("ios_theme") == "dark")
        self._shadow.setColor(QColor(0, 0, 0, 220 if dark else 110))

    def showEvent(self, ev) -> None:
        if not self._positioned:
            self._positioned = True
            parent = self.parentWidget()
            if parent is not None and parent.isVisible():
                screen = QApplication.screenAt(parent.frameGeometry().center())
            else:
                screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                # 小屏幕（例如 1366×768 / 125% 缩放）上按可用区域收一下尺寸，
                # 内容本身都有滚动条，不会因为窗口过大点不到底部按钮。
                max_w = max(480, area.width() - 20)
                max_h = max(420, area.height() - 20)
                if self.width() > max_w or self.height() > max_h:
                    self.resize(min(self.width(), max_w), min(self.height(), max_h))
                if parent is not None and parent.isVisible():
                    center = parent.frameGeometry().center()
                    x = center.x() - self.width() // 2
                    y = center.y() - self.height() // 2
                else:
                    x = area.center().x() - self.width() // 2
                    y = area.center().y() - self.height() // 2
                x = max(area.left(), min(x, area.right() - self.width()))
                y = max(area.top(), min(y, area.bottom() - self.height()))
                self.move(x, y)
        self._refresh_shadow()
        super().showEvent(ev)
