# -*- coding: utf-8 -*-
"""翻译结果悬浮窗。

无边框圆角卡片，可拖动、可置顶，显示原文与译文，提供复制 / 朗读 /
换语言 / 换引擎 / 重新识别等操作。
"""
from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import paths
from .langs import LANGS, TARGETS, display_name, label as lang_label
from .translate import engine_label, list_providers

MARGIN = 14          # 阴影留白


class _TitleBar(QWidget):
    """标题栏：按住可拖动整个窗口，双击回到截图位置。"""

    def __init__(self, window: "ResultWindow"):
        super().__init__(window)
        self._win = window
        self._offset: Optional[QPoint] = None
        self.setFixedHeight(34)
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._offset = ev.globalPos() - self._win.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._offset is not None and ev.buttons() & Qt.LeftButton:
            self._win.move(ev.globalPos() - self._offset)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._offset = None
        ev.accept()

    def mouseDoubleClickEvent(self, ev):
        self._win.reposition()
        ev.accept()


class ResultWindow(QWidget):
    retranslate = pyqtSignal(str, str, str)      # 原文, 源语言, 目标语言
    reocr = pyqtSignal()
    open_settings = pyqtSignal()
    hidden = pyqtSignal()

    def __init__(self, cfg, speaker=None, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self._cfg = cfg
        self._speaker = speaker
        self._notifier = None
        self._anchor: Optional[QRect] = None
        self._source_text = ""
        self._target_text = ""
        self._busy = False
        self._token = 0

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowIcon(QIcon(str(paths.icon_path())))
        self._build()
        self.apply_config()

    # ---------------------------------------------------------------- 构建

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        self.card = QFrame(self)
        self.card.setObjectName("Card")
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(9)

        # ---- 标题栏 ----
        bar = _TitleBar(self)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        self.title_icon = QLabel("译")
        self.title_icon.setFixedSize(20, 20)
        self.title_icon.setAlignment(Qt.AlignCenter)
        self.title_icon.setStyleSheet(
            "background:#4c8dff;color:#fff;border-radius:6px;font-weight:700;font-size:11px;")
        bl.addWidget(self.title_icon)

        self.title = QLabel("截图翻译")
        self.title.setObjectName("TitleLabel")
        bl.addWidget(self.title)
        bl.addStretch(1)

        self.btn_pin = QToolButton()
        self.btn_pin.setText("📌")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("窗口置顶")
        self.btn_pin.clicked.connect(self._on_pin)
        bl.addWidget(self.btn_pin)

        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙")
        self.btn_settings.setToolTip("打开设置")
        self.btn_settings.clicked.connect(self.open_settings.emit)
        bl.addWidget(self.btn_settings)

        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setToolTip("关闭 (Esc)")
        self.btn_close.clicked.connect(self.hide_window)
        bl.addWidget(self.btn_close)

        root.addWidget(bar)

        # ---- 语言行 ----
        lang_row = QHBoxLayout()
        lang_row.setSpacing(6)
        self.cmb_src = QComboBox()
        self.cmb_dst = QComboBox()
        for code, name in LANGS:
            self.cmb_src.addItem(name, code)
        for code, name in TARGETS:
            self.cmb_dst.addItem(name, code)
        self.cmb_src.setMinimumWidth(120)
        self.cmb_dst.setMinimumWidth(120)
        self.cmb_src.currentIndexChanged.connect(self._on_lang_changed)
        self.cmb_dst.currentIndexChanged.connect(self._on_lang_changed)

        self.btn_swap = QToolButton()
        self.btn_swap.setText("⇄")
        self.btn_swap.setToolTip("交换源语言与目标语言")
        self.btn_swap.clicked.connect(self._swap_langs)

        self.btn_retry = QPushButton("重新翻译")
        self.btn_retry.setProperty("accent", True)
        self.btn_retry.clicked.connect(self._emit_retranslate)

        lang_row.addWidget(self.cmb_src, 1)
        lang_row.addWidget(self.btn_swap)
        lang_row.addWidget(self.cmb_dst, 1)
        lang_row.addWidget(self.btn_retry)
        root.addLayout(lang_row)

        # ---- 原文 ----
        self.lbl_source = QLabel("原文")
        self.lbl_source.setProperty("role", "section")
        self.lbl_source.setCursor(Qt.PointingHandCursor)
        self.lbl_source.mousePressEvent = lambda e: self._toggle_source()  # type: ignore
        root.addWidget(self.lbl_source)

        self.view_source = QTextEdit()
        self.view_source.setObjectName("SourceView")
        self.view_source.setReadOnly(True)
        self.view_source.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view_source.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view_source.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self.view_source)

        # ---- 译文 ----
        self.view_trans = QTextEdit()
        self.view_trans.setObjectName("TransView")
        self.view_trans.setReadOnly(True)
        self.view_trans.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view_trans.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self.view_trans)

        # ---- 状态 ----
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("StatusLabel")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(30)      # 预留两行，长文本不会被切掉
        self.lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.lbl_status)

        # ---- 工具栏 ----
        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.btn_copy_trans = QPushButton("复制译文")
        self.btn_copy_trans.setProperty("accent", True)
        self.btn_copy_trans.clicked.connect(lambda: self._copy(self._target_text, self.btn_copy_trans))

        self.btn_copy_both = QPushButton("复制双语")
        self.btn_copy_both.clicked.connect(lambda: self._copy_both(self.btn_copy_both))

        self.btn_speak = QPushButton("🔊 朗读")
        self.btn_speak.clicked.connect(self._speak)

        self.btn_reocr = QPushButton("重新识别")
        self.btn_reocr.clicked.connect(self.reocr.emit)

        self.cmb_engine = QComboBox()
        self.cmb_engine.setToolTip("切换翻译引擎后会自动重新翻译")
        for key, name in list_providers():
            self.cmb_engine.addItem(name, key)
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_changed)

        tools.addWidget(self.btn_copy_trans)
        tools.addWidget(self.btn_copy_both)
        tools.addWidget(self.btn_speak)
        tools.addWidget(self.btn_reocr)
        tools.addStretch(1)
        tools.addWidget(self.cmb_engine)
        root.addLayout(tools)

        self._engine_dirty = False
        self.view_source.setVisible(False)
        self.lbl_source.setVisible(False)

    # ---------------------------------------------------------------- 配置

    def apply_config(self) -> None:
        ui = self._cfg.section("ui")
        width = int(ui.get("result_width", 560) or 560)
        self.setFixedWidth(width + MARGIN * 2)

        src = self._cfg.get("translate.source", "auto")
        dst = self._cfg.get("translate.target", "zh-CHS")
        self._select(self.cmb_src, src)
        self._select(self.cmb_dst, dst)

        engine = self._cfg.get("translate.engine", "auto")
        self._select(self.cmb_engine, engine)

        show_src = bool(ui.get("show_original", True))
        self._show_source = show_src
        self._apply_source_visibility()

        on_top = bool(ui.get("always_on_top", True))
        self.btn_pin.setChecked(on_top)
        self._apply_on_top(on_top)

    @staticmethod
    def _select(combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _apply_on_top(self, on_top: bool) -> None:
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    def _on_pin(self) -> None:
        on_top = self.btn_pin.isChecked()
        self._apply_on_top(on_top)
        self._cfg.set("ui.always_on_top", on_top)

    def _apply_source_visibility(self) -> None:
        show = getattr(self, "_show_source", True)
        has = bool(self._source_text.strip())
        self.view_source.setVisible(show and has)
        self.lbl_source.setVisible(show and has)
        self.lbl_source.setText("▾ 原文（点击折叠）" if show else "▸ 原文")

    def _toggle_source(self) -> None:
        self._show_source = not getattr(self, "_show_source", True)
        self._cfg.set("ui.show_original", self._show_source)
        self._apply_source_visibility()
        self._fit()

    # ---------------------------------------------------------------- 状态

    def set_anchor(self, rect: Optional[QRect]) -> None:
        self._anchor = QRect(rect) if rect else None

    def show_loading(self, stage: str = "正在识别文字…") -> None:
        self._busy = True
        self._token += 1
        self.title.setText("截图翻译")
        self.view_trans.setPlainText("")
        self.view_source.setPlainText(self._source_text)
        self._set_status(stage, "busy")
        self.btn_retry.setEnabled(False)
        self._show_and_position()

    def show_result(self, ocr_result, translate_result, elapsed_note: str = "") -> None:
        self._busy = False
        self._source_text = ocr_result.text or ""
        self._target_text = translate_result.text or ""

        self.view_source.setPlainText(self._source_text)
        self.view_trans.setPlainText(self._target_text)
        self._apply_source_visibility()

        # 状态栏只放最要紧的信息，完整明细放进悬浮提示，避免一行放不下被截断
        brief = []
        if translate_result.engine:
            brief.append(engine_label(translate_result.engine))
        brief.append("%.2fs" % translate_result.elapsed)
        if translate_result.note:
            brief.append(translate_result.note)
        self._set_status(" · ".join(brief), "ok")

        detail = []
        if getattr(ocr_result, "elapsed", 0):
            detail.append("识别耗时 %.2fs" % ocr_result.elapsed)
        if getattr(ocr_result, "box_count", 0):
            detail.append("识别到 %d 个文本块" % ocr_result.box_count)
        if translate_result.detected:
            detail.append("检测语言：%s" % lang_label(translate_result.detected))
        detail.append("OCR 引擎：%s" % (getattr(ocr_result, "engine", "") or "-"))
        detail.append("翻译引擎：%s" % engine_label(translate_result.engine))
        if elapsed_note:
            detail.append(elapsed_note)
        self.lbl_status.setToolTip("\n".join(detail))

        self.btn_retry.setEnabled(True)
        self._fit()
        self._show_and_position()

        if self._cfg.get("ui.auto_copy", False) and self._target_text:
            QApplication.clipboard().setText(self._target_text)
            self._flash(self.btn_copy_trans, "已自动复制 ✓")

    def show_text_result(self, source_text: str, translate_result,
                         ocr_label: str = "剪贴板") -> None:
        class _R:
            text = source_text
            box_count = 0
            elapsed = 0.0

        self.title.setText(ocr_label)
        self.show_result(_R(), translate_result)

    def show_error(self, stage: str, message: str) -> None:
        self._busy = False
        head = "识别失败" if stage == "ocr" else "翻译失败"
        self._set_status("%s：%s" % (head, message), "error")
        if not self.view_trans.toPlainText():
            self.view_trans.setPlainText("")
        self.btn_retry.setEnabled(True)
        self._fit()
        self._show_and_position()
        if self._cfg.get("behavior.notify", True):
            self._notify(head, message[:150])

    def init(self, speaker=None, notifier=None) -> None:
        """由 AppContext 注入可选协作对象。"""
        if speaker is not None:
            self._speaker = speaker
        if notifier is not None:
            self._notifier = notifier

    def _notify(self, title: str, message: str) -> None:
        if self._notifier is None:
            return
        if not self._cfg.get("behavior.notify", True):
            return
        try:
            self._notifier(title, message)
        except Exception:
            pass

    def _set_status(self, text: str, state: str = "") -> None:
        self.lbl_status.setText(text)
        self.lbl_status.setProperty("state", state)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    # ---------------------------------------------------------------- 布局

    def _fit(self) -> None:
        self._fit_view(self.view_source, 150)
        self._fit_view(self.view_trans, 100000)
        self.layout().activate()
        self.adjustSize()
        self._clamp_height()

    def _fit_view(self, view: QTextEdit, max_height: int) -> None:
        if not view.isVisible():
            view.setFixedHeight(1)
            return
        doc = view.document()
        doc.setTextWidth(max(80, view.viewport().width()))
        h = int(doc.size().height()) + 18
        view.setFixedHeight(max(40, min(h, max_height)))

    def _clamp_height(self) -> None:
        screen = self._screen_for_anchor()
        limit = int(screen.availableGeometry().height() * 0.86) if screen else 900
        if self.height() > limit:
            self.setFixedHeight(limit)
            self.view_trans.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.view_trans.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _screen_for_anchor(self):
        anchor = self._anchor
        if anchor is not None:
            for s in QGuiApplication.screens():
                if s.geometry().contains(anchor.center()):
                    return s
        return QGuiApplication.primaryScreen()

    def _show_and_position(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.reposition()

    def reposition(self) -> None:
        screen = self._screen_for_anchor()
        if screen is None:
            return
        area: QRect = screen.availableGeometry()
        w, h = self.width(), self.height()
        anchor = self._anchor
        if anchor is None or not anchor.isValid():
            x = area.center().x() - w // 2
            y = area.center().y() - h // 2
        else:
            x = anchor.left()
            y = anchor.bottom() + 10
            if y + h > area.bottom() - 4:
                y = anchor.top() - h - 10
            if y < area.top() + 4:
                y = min(area.bottom() - h - 4, anchor.bottom() + 10)
        x = max(area.left() + 4, min(x, area.right() - w - 4))
        y = max(area.top() + 4, min(y, area.bottom() - h - 4))
        self.move(int(x), int(y))

    # ---------------------------------------------------------------- 交互

    def keyPressEvent(self, ev) -> None:
        key = ev.key()
        mods = ev.modifiers()
        if key == Qt.Key_Escape:
            self.hide_window()
            return
        if key == Qt.Key_C and mods & Qt.ControlModifier and not (
                self.view_trans.hasFocus() and self.view_trans.textCursor().hasSelection()):
            self._copy(self._target_text, self.btn_copy_trans)
            return
        if key == Qt.Key_R and mods & Qt.ControlModifier:
            self._emit_retranslate()
            return
        super().keyPressEvent(ev)

    def hide_window(self) -> None:
        if self._speaker is not None:
            self._speaker.stop()
        self.hide()
        self.hidden.emit()

    def closeEvent(self, ev):
        ev.ignore()
        self.hide_window()

    def _on_lang_changed(self, _idx) -> None:
        src = self.cmb_src.currentData()
        dst = self.cmb_dst.currentData()
        self._cfg.set("translate.source", src)
        self._cfg.set("translate.target", dst)
        if self._source_text.strip():
            self._emit_retranslate()

    def _swap_langs(self) -> None:
        src = self.cmb_src.currentData()
        dst = self.cmb_dst.currentData()
        if src == "auto":
            src = dst
        new_dst = src
        self._select(self.cmb_src, dst)
        self._select(self.cmb_dst, new_dst)

    def _on_engine_changed(self, _idx) -> None:
        engine = self.cmb_engine.currentData()
        self._cfg.set("translate.engine", engine)
        if self._source_text.strip():
            self._emit_retranslate()

    def _emit_retranslate(self) -> None:
        if not self._source_text.strip():
            return
        self.retranslate.emit(self._source_text, self.cmb_src.currentData(),
                              self.cmb_dst.currentData())

    def _speak(self) -> None:
        if self._speaker is None:
            return
        text = self._target_text or self._source_text
        if not text:
            return
        lang = self.cmb_dst.currentData() if self._target_text else self.cmb_src.currentData()
        self._speaker.speak(text, "en" if lang == "auto" else lang)

    # ---------------------------------------------------------------- 剪贴板

    def _copy(self, text: str, button: Optional[QPushButton] = None) -> None:
        if not text:
            return
        QApplication.clipboard().setText(text)
        if button is not None:
            self._flash(button, "已复制 ✓")

    def _copy_both(self, button: Optional[QPushButton] = None) -> None:
        parts = []
        if self._source_text.strip():
            parts.append(self._source_text.strip())
        if self._target_text.strip():
            parts.append(self._target_text.strip())
        self._copy("\n\n".join(parts), button)

    def _flash(self, button: QPushButton, text: str) -> None:
        if not button.property("_orig_text"):
            button.setProperty("_orig_text", button.text())
        original = str(button.property("_orig_text"))
        button.setText(text)
        QTimer.singleShot(1400, lambda: button.setText(original))
