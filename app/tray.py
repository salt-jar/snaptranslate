# -*- coding: utf-8 -*-
"""系统托盘图标与菜单。"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from . import paths


def app_icon() -> QIcon:
    """加载程序图标；文件缺失时用文字图标兜底，保证托盘一定显示得出来。"""
    path = paths.icon_path()
    if path.exists():
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon

    from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap

    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor(76, 141, 255))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 16, 16)
    f = QFont("Microsoft YaHei", 30)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255))
    p.drawText(pm.rect(), Qt.AlignCenter, "译")
    p.end()
    return QIcon(pm)


def message_icon() -> QIcon:
    """系统通知要求标准尺寸图标。

    Qt 的 Windows 托盘后端会检查图标的实际像素尺寸；高 DPI 模式下
    ``QIcon.pixmap(48, 48)`` 返回的是 96x96（DPR=2），因此必须把
    devicePixelRatio 重置为 1，否则会打印 "Wrong icon size (96x96)" 警告。
    """
    pm = app_icon().pixmap(48, 48)
    if pm.isNull():
        return app_icon()
    pm.setDevicePixelRatio(1.0)
    if pm.width() != 48 or pm.height() != 48:
        pm = pm.scaled(48, 48, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(1.0)
    return QIcon(pm)


class Tray(QSystemTrayIcon):
    capture = pyqtSignal()
    clipboard = pyqtSignal()
    repeat = pyqtSignal()
    settings = pyqtSignal()
    create_shortcut = pyqtSignal()
    toggle_autostart = pyqtSignal(bool)
    quit_app = pyqtSignal()
    about = pyqtSignal()

    def __init__(self, cfg, parent=None):
        super().__init__(app_icon(), parent)
        self._cfg = cfg
        self.setToolTip("截译 · 截图翻译\n%s" % self._hotkey_tip())
        self._menu = QMenu()
        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _hotkey_tip(self) -> str:
        hk = self._cfg.get("hotkeys.capture", "")
        return ("按 %s 开始截图翻译" % hk) if hk else "右键菜单里可以开始截图翻译"

    def _act(self, menu: QMenu, text: str, slot=None, checkable: bool = False,
             checked: bool = False) -> QAction:
        act = QAction(text, menu)
        if checkable:
            act.setCheckable(True)
            act.setChecked(checked)
        if slot is not None:
            act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_menu(self) -> None:
        m = self._menu
        hk = self._cfg.get("hotkeys.capture", "")
        clip = self._cfg.get("hotkeys.clipboard", "")
        rep = self._cfg.get("hotkeys.repeat", "")

        self._act(m, "截图翻译%s" % ("   %s" % hk if hk else ""), self.capture.emit)
        self._act(m, "翻译剪贴板%s" % ("   %s" % clip if clip else ""), self.clipboard.emit)
        self._act(m, "重译上次区域%s" % ("   %s" % rep if rep else ""), self.repeat.emit)
        m.addSeparator()
        self._act(m, "设置…", self.settings.emit)
        self._act(m, "创建桌面快捷方式", self.create_shortcut.emit)
        self.act_autostart = self._act(
            m, "开机自动启动", self._on_autostart, checkable=True,
            checked=paths.is_autostart_enabled(),
        )
        m.addSeparator()
        self._act(m, "关于", self.about.emit)
        self._act(m, "退出", self.quit_app.emit)

    def _on_autostart(self, checked: bool) -> None:
        self.toggle_autostart.emit(checked)

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.capture.emit()

    def refresh(self) -> None:
        """配置变更后重建菜单文字与提示。"""
        self._menu.clear()
        self._build_menu()
        self.setToolTip("截译 · 截图翻译\n%s" % self._hotkey_tip())
