# -*- coding: utf-8 -*-
"""应用上下文：把配置、热键、抓屏、OCR/翻译流水线、托盘和窗口串起来。"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QObject, QRect, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox

from . import paths, shortcut
from .cache import LRUCache
from .hotkeys import HotkeyManager
from .overlay import CaptureOverlay
from .pipeline import Pipeline
from .result_window import ResultWindow
from .screen import ScreenMapper
from .settings_window import SettingsDialog
from .speech import Speaker
from .theme import stylesheet
from .tray import Tray, app_icon, message_icon

log = logging.getLogger("snaptranslate.ctx")

#: 动作名 -> 托盘菜单里的中文说明
ACTION_NAMES = {
    "capture": "截图翻译",
    "clipboard": "翻译剪贴板",
    "repeat": "重译上次区域",
    "toggle_window": "显示/隐藏结果窗口",
}


class AppContext(QObject):
    def __init__(self, app: QApplication, cfg, parent=None):
        super().__init__(parent)
        self.app = app
        self.cfg = cfg

        self.mapper = ScreenMapper()
        self.speaker = Speaker(self)
        self.pipeline = Pipeline(cfg, self)
        self.result = ResultWindow(cfg, self.speaker)
        self.tray = Tray(cfg, self)
        self.hotkeys = HotkeyManager(self)

        self._overlay: Optional[CaptureOverlay] = None
        self._settings: Optional[SettingsDialog] = None
        self._pending_anchor: Optional[QRect] = None
        self._last_image = None
        self._clip_cache = LRUCache(50)

        self.hotkey_conflicts: Dict[str, str] = {}
        self.hotkey_backend: str = ""

        self.result.init(speaker=self.speaker, notifier=self.notify)
        self._wire()

    # ---------------------------------------------------------------- 装配

    def _wire(self) -> None:
        self.tray.capture.connect(self.do_capture)
        self.tray.clipboard.connect(self.do_clipboard)
        self.tray.repeat.connect(self.do_repeat)
        self.tray.settings.connect(self.open_settings)
        self.tray.create_shortcut.connect(self.create_desktop_shortcut)
        self.tray.toggle_autostart.connect(self._on_autostart)
        self.tray.about.connect(self.show_about)
        self.tray.quit_app.connect(self.quit)

        self.hotkeys.triggered.connect(self._on_hotkey)
        self.hotkeys.conflicts.connect(self._on_hotkey_conflicts)
        self.hotkeys.backend_changed.connect(self._on_hotkey_backend)

        self.pipeline.ocr_done.connect(self._on_ocr_done)
        self.pipeline.finished.connect(self._on_finished)
        self.pipeline.failed.connect(self._on_failed)

        self.result.retranslate.connect(self._on_retranslate)
        self.result.reocr.connect(self.do_repeat)
        self.result.open_settings.connect(self.open_settings)

    def start(self) -> None:
        self.tray.show()
        self.apply_hotkeys()
        if self.cfg.get("behavior.notify", True):
            tips = []
            hk = self.cfg.get("hotkeys.capture", "")
            if hk:
                tips.append("按 %s 截图翻译" % hk)
            tips.append("右键托盘图标可打开菜单")
            QTimer.singleShot(600, lambda: self.notify("截译已启动", " · ".join(tips)))

    def apply_theme(self) -> None:
        self.app.setStyleSheet(stylesheet(
            str(self.cfg.get("ui.theme", "dark")),
            int(self.cfg.get("ui.font_size", 12) or 12),
        ))

    # ---------------------------------------------------------------- 热键

    def apply_hotkeys(self) -> None:
        bindings = {
            action: str(self.cfg.get("hotkeys.%s" % action, "") or "")
            for action in ACTION_NAMES
        }
        if not self.cfg.get("hotkeys.enabled", True):
            self.hotkeys.stop()
            self.hotkey_backend = "已禁用"
            return
        mode = str(self.cfg.get("hotkeys.mode", "auto"))
        self.hotkey_conflicts = self.hotkeys.apply(bindings, mode)
        self.tray.refresh()

    def _on_hotkey(self, action: str) -> None:
        log.info("快捷键触发：%s", action)
        handler = {
            "capture": self.do_capture,
            "clipboard": self.do_clipboard,
            "repeat": self.do_repeat,
            "toggle_window": self.toggle_result_window,
        }.get(action)
        if handler:
            handler()

    def _on_hotkey_conflicts(self, conflicts: dict) -> None:
        self.hotkey_conflicts = dict(conflicts)
        if conflicts and self.cfg.get("behavior.notify", True):
            lines = ["%s（%s）" % (ACTION_NAMES.get(a, a), r) for a, r in conflicts.items()]
            self.notify("快捷键未能生效", "；".join(lines) + "。请在设置里换一个组合键。")

    def _on_hotkey_backend(self, desc: str) -> None:
        self.hotkey_backend = desc

    # ---------------------------------------------------------------- 截图

    def do_capture(self) -> None:
        if self._overlay is not None:
            return
        # 先把自己的窗口藏起来，免得被拍进截图
        if self.result.isVisible():
            self.result.hide()
        QTimer.singleShot(180, self._start_overlay)

    def _start_overlay(self) -> None:
        if self._overlay is not None:
            return
        try:
            self.mapper.refresh()
            overlay = CaptureOverlay(
                self.mapper,
                show_magnifier=bool(self.cfg.get("ui.magnifier", True)),
                show_hint=bool(self.cfg.get("ui.overlay_hint", True)),
            )
        except Exception as e:  # noqa: BLE001
            self.notify("截图失败", "无法抓取屏幕：%s" % e)
            return
        overlay.captured.connect(self._on_captured)
        overlay.cancelled.connect(self._on_capture_cancelled)
        overlay.destroyed.connect(lambda *_: setattr(self, "_overlay", None))
        self._overlay = overlay
        overlay.start()

    def _on_captured(self, rect: QRect, image) -> None:
        overlay, self._overlay = self._overlay, None
        if overlay is not None:
            overlay.deleteLater()
        if image is None or image.isNull():
            self.notify("截图失败", "没有拿到图像")
            return

        self._last_image = image
        self._pending_anchor = QRect(rect)
        self.cfg.set("behavior.last_region",
                     [rect.x(), rect.y(), rect.width(), rect.height()])
        self.result.set_anchor(rect)
        self.result.title.setText("截图翻译")
        self.result.show_loading("正在识别文字…")

        self.pipeline.run(
            image,
            str(self.cfg.get("translate.source", "auto")),
            str(self.cfg.get("translate.target", "zh-CHS")),
            str(self.cfg.get("translate.engine", "auto")),
            str(self.cfg.get("ocr.engine", "auto")),
        )

    def _on_capture_cancelled(self) -> None:
        self._overlay = None

    def do_repeat(self) -> None:
        region = self.cfg.get("behavior.last_region")
        if not region:
            self.notify("没有可重译的区域", "请先用快捷键完成一次截图翻译")
            return
        try:
            rect = QRect(int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        except Exception:
            self.notify("没有可重译的区域", "上次区域记录已损坏")
            return
        self.mapper.refresh()
        image = self.mapper.grab_region(rect)
        if image.isNull():
            self.notify("重译失败", "上次的区域已经不在屏幕上了")
            return
        self._on_captured(rect, image)

    # ---------------------------------------------------------------- 剪贴板

    def do_clipboard(self) -> None:
        text = QApplication.clipboard().text() or ""
        if not text.strip():
            self.notify("剪贴板是空的", "先复制一段文字，再按快捷键")
            return
        self._pending_anchor = None
        self.result.set_anchor(self._focused_screen_rect())
        self.result.title.setText("剪贴板翻译")
        self.result.show_loading("正在翻译剪贴板内容…")
        self.pipeline.run_text_only(
            text.strip(),
            str(self.cfg.get("translate.source", "auto")),
            str(self.cfg.get("translate.target", "zh-CHS")),
            str(self.cfg.get("translate.engine", "auto")),
        )

    def _focused_screen_rect(self) -> QRect:
        from PyQt5.QtGui import QCursor

        pos = QCursor.pos()
        return QRect(pos.x() - 2, pos.y() - 2, 4, 4)

    def toggle_result_window(self) -> None:
        if self.result.isVisible():
            self.result.hide_window()
        else:
            self.result._show_and_position()

    # ---------------------------------------------------------------- 流水线回调

    def _on_ocr_done(self, ocr_result, elapsed: float) -> None:
        log.info("识别完成：%.2fs，%d 个文本块，%d 字符",
                 elapsed, len(ocr_result.boxes), len(ocr_result.text or ""))
        self.result.show_loading("正在翻译…")

    def _on_finished(self, ocr_result, translate_result) -> None:
        log.info("翻译完成：引擎=%s 耗时=%.2fs 检测=%s 结果=%d 字符 %s",
                 translate_result.engine, translate_result.elapsed,
                 translate_result.detected or "-", len(translate_result.text or ""),
                 ("（" + translate_result.note + "）") if translate_result.note else "")
        self.result.show_result(ocr_result, translate_result)

    def _on_failed(self, stage: str, message: str) -> None:
        log.warning("%s 阶段失败：%s", stage, message)
        self.result.show_error(stage, message)

    def _on_retranslate(self, text: str, src: str, dst: str) -> None:
        self.result.show_loading("正在重新翻译…")
        self.pipeline.run_text_only(
            text, src, dst, str(self.cfg.get("translate.engine", "auto"))
        )

    # ---------------------------------------------------------------- 设置

    def open_settings(self) -> None:
        if self._settings is None:
            self._settings = SettingsDialog(self.cfg, ctx=self, parent=None)
            self._settings.saved.connect(self.reload_config)
            self._settings.finished.connect(self._on_settings_closed)
        self._settings._load()
        self._settings._refresh_hotkey_status()
        self._settings.show()
        self._settings.raise_()
        self._settings.activateWindow()

    def _on_settings_closed(self, _result) -> None:
        self._settings = None

    def reload_config(self) -> None:
        self.apply_theme()
        self.result.apply_config()
        self.apply_hotkeys()
        from .translate import set_cache_size

        set_cache_size(int(self.cfg.get("behavior.cache_size", 300) or 300))

    # ---------------------------------------------------------------- 其它

    def notify(self, title: str, message: str) -> None:
        try:
            self.tray.showMessage(title, message, message_icon(), 4000)
        except Exception:
            pass

    def create_desktop_shortcut(self) -> None:
        ok, msg = shortcut.create_shortcut()
        self.notify("桌面快捷方式" if ok else "创建失败", msg)

    def _on_autostart(self, checked: bool) -> None:
        ok = paths.set_autostart(checked)
        if not ok:
            self.notify("设置失败", "无法写入开机启动项，请检查权限")
            self.tray.act_autostart.setChecked(not checked)

    def show_about(self) -> None:
        box = QMessageBox()
        box.setWindowTitle("关于 截译")
        box.setIconPixmap(app_icon().pixmap(64, 64))
        box.setTextFormat(True)
        box.setText(
            "<h3>截译 · 截图翻译 %s</h3>"
            "<p>按快捷键框选屏幕上的任意文字，自动识别并翻译。</p>"
            "<p style='color:#888'>配置文件：%s</p>" % (paths.APP_VERSION, paths.config_path())
        )
        box.setInformativeText(
            "快捷键：%s\n注册方式：%s\nOCR 引擎：%s\n翻译引擎：%s"
            % (self.cfg.get("hotkeys.capture", "未设置") or "未设置",
               self.hotkey_backend or "未知",
               self.cfg.get("ocr.engine", "auto"),
               self.cfg.get("translate.engine", "auto"))
        )
        box.exec_()

    def quit(self) -> None:
        self.hotkeys.stop()
        self.speaker.stop()
        self.pipeline.cancel()
        self.cfg.save()
        self.tray.hide()
        self.app.quit()
