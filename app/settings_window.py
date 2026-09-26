# -*- coding: utf-8 -*-
"""设置窗口。"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import paths, shortcut
from .hotkeys import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, format_hotkey
from .langs import LANGS, RAPID_LANGS, TARGETS
from .ocr import engine_status, list_engines
from .translate import list_providers, provider_status

# --------------------------------------------------------------------- 快捷键录制

_QT_TO_VK = {
    Qt.Key_Space: 0x20, Qt.Key_Tab: 0x09, Qt.Key_Return: 0x0D, Qt.Key_Enter: 0x0D,
    Qt.Key_Delete: 0x2E, Qt.Key_Insert: 0x2D, Qt.Key_Home: 0x24, Qt.Key_End: 0x23,
    Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22,
    Qt.Key_Up: 0x26, Qt.Key_Down: 0x28, Qt.Key_Left: 0x25, Qt.Key_Right: 0x27,
    Qt.Key_QuoteLeft: 0xC0, Qt.Key_Minus: 0xBD, Qt.Key_Equal: 0xBB,
    Qt.Key_BracketLeft: 0xDB, Qt.Key_BracketRight: 0xDD, Qt.Key_Backslash: 0xDC,
    Qt.Key_Semicolon: 0xBA, Qt.Key_Apostrophe: 0xDE, Qt.Key_Comma: 0xBC,
    Qt.Key_Period: 0xBE, Qt.Key_Slash: 0xBF,
}


def qt_key_to_hotkey(key: int, mods) -> Optional[str]:
    m = 0
    if mods & Qt.ControlModifier:
        m |= MOD_CONTROL
    if mods & Qt.AltModifier:
        m |= MOD_ALT
    if mods & Qt.ShiftModifier:
        m |= MOD_SHIFT
    if mods & Qt.MetaModifier:
        m |= MOD_WIN

    if 0x41 <= key <= 0x5A or 0x30 <= key <= 0x39:
        vk = key
    elif Qt.Key_F1 <= key <= Qt.Key_F24:
        vk = 0x70 + (key - Qt.Key_F1)
    else:
        vk = _QT_TO_VK.get(key)
    if vk is None:
        return None
    if m == 0 and not (0x70 <= vk <= 0x87):
        return None      # 必须带修饰键，避免抢走普通按键
    return format_hotkey(m, vk)


class HotkeyEdit(QLineEdit):
    """点击后直接按组合键即可录制的输入框。"""

    def __init__(self, value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("HotkeyEdit")
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处，然后按下组合键")
        self.setToolTip("按 Backspace / Delete / Esc 可清空")
        self.setText(value)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(180)

    def keyPressEvent(self, ev):
        key = ev.key()
        if key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape):
            self.setText("")
            return
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_unknown):
            return
        text = qt_key_to_hotkey(key, ev.modifiers())
        if text:
            self.setText(text)
        ev.accept()

    def mousePressEvent(self, ev):
        self.setFocus(Qt.MouseFocusReason)
        ev.accept()


# --------------------------------------------------------------------- 辅助构建


def _form(rows: List[Tuple[str, QWidget]]) -> QWidget:
    box = QWidget()
    lay = QFormLayout(box)
    lay.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    for text, widget in rows:
        if text:
            lab = QLabel(text)
            lab.setProperty("role", "hint")
            lay.addRow(lab, widget)
        else:
            lay.addRow(widget)
    return box


def _group(title: str, inner: QWidget) -> QGroupBox:
    box = QGroupBox(title)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(12, 8, 12, 12)
    lay.addWidget(inner)
    return box


def _label(text: str, role: str = "hint") -> QLabel:
    lab = QLabel(text)
    lab.setProperty("role", role)
    lab.setWordWrap(True)
    return lab


# --------------------------------------------------------------------- 主对话框


class SettingsDialog(QDialog):
    saved = pyqtSignal()

    def __init__(self, cfg, ctx=None, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._ctx = ctx
        self.setWindowTitle("截译 · 设置")
        self.setWindowIcon(QIcon(str(paths.icon_path())))
        self.setMinimumSize(680, 620)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_hotkeys(), "快捷键")
        self.tabs.addTab(self._tab_ocr(), "文字识别")
        self.tabs.addTab(self._tab_translate(), "翻译引擎")
        self.tabs.addTab(self._tab_ui(), "外观")
        self.tabs.addTab(self._tab_system(), "系统")
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.lbl_footer = _label("")
        bottom.addWidget(self.lbl_footer, 1)

        btn_reset = QPushButton("恢复默认")
        btn_reset.clicked.connect(self._reset)
        bottom.addWidget(btn_reset)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        btn_save = QPushButton("保存")
        btn_save.setProperty("accent", True)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        bottom.addWidget(btn_save)
        root.addLayout(bottom)

        self._load()

    # ------------------------------------------------------------ 快捷键页

    def _tab_hotkeys(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(10, 12, 10, 10)
        root.setSpacing(12)

        hk = self._cfg.section("hotkeys")
        self.ed_capture = HotkeyEdit(hk.get("capture", ""))
        self.ed_clipboard = HotkeyEdit(hk.get("clipboard", ""))
        self.ed_repeat = HotkeyEdit(hk.get("repeat", ""))

        root.addWidget(_group("全局快捷键", _form([
            ("截图并翻译", self.ed_capture),
            ("翻译剪贴板内容", self.ed_clipboard),
            ("重译上次区域", self.ed_repeat),
        ])))

        self.cmb_hkmode = QComboBox()
        self.cmb_hkmode.addItem("自动（推荐：优先系统热键，失败时用键盘钩子）", "auto")
        self.cmb_hkmode.addItem("仅系统热键（不占用按键，最干净）", "native")
        self.cmb_hkmode.addItem("仅键盘钩子（与其它软件冲突时用）", "listener")
        root.addWidget(_group("注册方式", _form([
            ("", self.cmb_hkmode),
            ("", _label(
                "说明：系统热键（RegisterHotKey）会把按键从其它程序那里抢过来，"
                "QQ / 微信等截图工具的默认快捷键常被占用（如 Ctrl+Alt+A）。"
                "遇到占用时程序会自动改用键盘钩子模式，此时按键仍会传给当前窗口。")),
        ])))

        self.lbl_hk_status = _label("")
        root.addWidget(_group("当前状态", self.lbl_hk_status))
        root.addStretch(1)
        return page

    # ------------------------------------------------------------ 识别页

    def _tab_ocr(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(10, 12, 10, 10)
        root.setSpacing(12)

        self.cmb_ocr = QComboBox()
        for key, name in list_engines():
            self.cmb_ocr.addItem(name, key)

        status = engine_status()
        lines = []
        for key, text in status.items():
            lines.append("%s：%s" % (key, text))

        self.cmb_ocr_lang = QComboBox()
        for key, name in RAPID_LANGS:
            self.cmb_ocr_lang.addItem(name, key)

        self.sp_upscale = QDoubleSpinBox()
        self.sp_upscale.setRange(1.0, 4.0)
        self.sp_upscale.setSingleStep(0.5)
        self.sp_upscale.setDecimals(1)
        self.sp_upscale.setSuffix(" 倍")
        self.sp_upscale.setToolTip("截图越小越应该放大，能显著提升小字号识别率")

        self.sp_threshold = QSpinBox()
        self.sp_threshold.setRange(200, 4000)
        self.sp_threshold.setSingleStep(100)
        self.sp_threshold.setSuffix(" px")
        self.sp_threshold.setToolTip("图像最长边小于该值时才放大")

        self.chk_enhance = QCheckBox("灰度 + 对比度增强（深色主题自动反色）")
        self.chk_angle = QCheckBox("自动判断文字方向（处理倒置/竖排）")
        self.chk_merge = QCheckBox("按行归并，保持阅读顺序")

        self.sp_score = QDoubleSpinBox()
        self.sp_score.setRange(0.0, 1.0)
        self.sp_score.setSingleStep(0.05)
        self.sp_score.setDecimals(2)
        self.sp_score.setToolTip("调低可以识别到更淡/更小的文字，但也更容易出错")

        root.addWidget(_group("引擎", _form([
            ("识别引擎", self.cmb_ocr),
            ("语言", self.cmb_ocr_lang),
            ("", _label("检测结果：\n" + "\n".join(lines))),
        ])))

        root.addWidget(_group("图像预处理", _form([
            ("放大倍数", self.sp_upscale),
            ("放大阈值", self.sp_threshold),
            ("", self.chk_enhance),
        ])))

        root.addWidget(_group("识别选项", _form([
            ("", self.chk_angle),
            ("", self.chk_merge),
            ("置信度阈值", self.sp_score),
        ])))
        root.addStretch(1)
        return page

    # ------------------------------------------------------------ 翻译页

    def _tab_translate(self) -> QWidget:
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        page = QWidget()
        scroll.setWidget(page)
        outer_lay.addWidget(scroll)

        root = QVBoxLayout(page)
        root.setContentsMargins(10, 12, 10, 10)
        root.setSpacing(12)

        self.cmb_engine = QComboBox()
        for key, name in list_providers():
            self.cmb_engine.addItem(name, key)

        self.cmb_src = QComboBox()
        self.cmb_dst = QComboBox()
        for code, name in LANGS:
            self.cmb_src.addItem(name, code)
        for code, name in TARGETS:
            self.cmb_dst.addItem(name, code)

        self.chk_fallback = QCheckBox("失败时自动切换其它免费引擎（推荐）")

        self.sp_timeout = QSpinBox()
        self.sp_timeout.setRange(3, 120)
        self.sp_timeout.setSuffix(" 秒")

        status = provider_status(self._cfg.data)
        stat_lines = ["%s：%s" % (k, v) for k, v in status.items()]

        self.btn_test = QPushButton("测试当前配置")
        self.btn_test.clicked.connect(self._test_translate)
        self.lbl_test = _label("")

        root.addWidget(_group("基本设置", _form([
            ("翻译引擎", self.cmb_engine),
            ("源语言", self.cmb_src),
            ("目标语言", self.cmb_dst),
            ("超时", self.sp_timeout),
            ("", self.chk_fallback),
            ("", self.btn_test),
            ("", self.lbl_test),
            ("", _label("引擎状态：\n" + "\n".join(stat_lines))),
        ])))

        t = self._cfg.section("translate")
        llm = t.get("llm") or {}
        self.ed_llm_url = QLineEdit(llm.get("base_url", ""))
        self.ed_llm_url.setPlaceholderText("https://api.deepseek.com/v1")
        self.ed_llm_key = QLineEdit(llm.get("api_key", ""))
        self.ed_llm_key.setEchoMode(QLineEdit.Password)
        self.ed_llm_key.setPlaceholderText("sk-...")
        self.ed_llm_model = QLineEdit(llm.get("model", ""))
        self.ed_llm_model.setPlaceholderText("deepseek-chat")
        self.txt_llm_prompt = QPlainTextEdit(llm.get("prompt", ""))
        self.txt_llm_prompt.setFixedHeight(96)
        self.txt_llm_prompt.setPlaceholderText("系统提示词，可用 {target} 代表目标语言")

        root.addWidget(_group("AI 大模型翻译（质量最好，推荐）", _form([
            ("接口地址", self.ed_llm_url),
            ("API Key", self.ed_llm_key),
            ("模型名", self.ed_llm_model),
            ("提示词", self.txt_llm_prompt),
            ("", _label("兼容 OpenAI 协议的服务都可以填：DeepSeek(api.deepseek.com/v1)、"
                        "Kimi(api.moonshot.cn/v1)、通义(dashscope.aliyuncs.com/compatible-mode/v1)、"
                        "智谱(open.bigmodel.cn/api/paas/v4)、硅基流动(api.siliconflow.cn/v1)。")),
        ])))

        bd = t.get("baidu") or {}
        self.ed_bd_appid = QLineEdit(bd.get("appid", ""))
        self.ed_bd_key = QLineEdit(bd.get("key", ""))
        self.ed_bd_key.setEchoMode(QLineEdit.Password)
        root.addWidget(_group("百度翻译开放平台（可选）", _form([
            ("APPID", self.ed_bd_appid),
            ("密钥", self.ed_bd_key),
        ])))

        yd = t.get("youdao_official") or {}
        self.ed_yd_appkey = QLineEdit(yd.get("appkey", ""))
        self.ed_yd_secret = QLineEdit(yd.get("secret", ""))
        self.ed_yd_secret.setEchoMode(QLineEdit.Password)
        root.addWidget(_group("有道智云（可选）", _form([
            ("应用 ID", self.ed_yd_appkey),
            ("应用密钥", self.ed_yd_secret),
        ])))

        cu = t.get("custom") or {}
        self.ed_cu_url = QLineEdit(cu.get("url", ""))
        self.ed_cu_method = QComboBox()
        self.ed_cu_method.addItems(["POST", "GET"])
        self.ed_cu_method.setCurrentText(str(cu.get("method", "POST")).upper())
        self.ed_cu_headers = QLineEdit(str(cu.get("headers", "")))
        self.ed_cu_body = QLineEdit(str(cu.get("body", "")))
        self.ed_cu_path = QLineEdit(str(cu.get("result_path", "")))
        root.addWidget(_group("自定义 HTTP 接口（可选）", _form([
            ("接口地址", self.ed_cu_url),
            ("方法", self.ed_cu_method),
            ("请求头(JSON)", self.ed_cu_headers),
            ("请求体模板", self.ed_cu_body),
            ("结果路径", self.ed_cu_path),
            ("", _label("请求体里可用 {text} / {from} / {to} 占位；"
                        "结果路径用点号取，例如 data.translation")),
        ])))

        root.addStretch(1)
        return outer

    def _test_translate(self) -> None:
        self.btn_test.setEnabled(False)
        self.lbl_test.setText("测试中…")
        self.lbl_test.setProperty("state", "")
        cfg = self._collect_translate_cfg()
        src = self.cmb_src.currentData()
        dst = self.cmb_dst.currentData()

        def work():
            from .translate import translate

            try:
                res = translate("Hello world, this is a screenshot translation test.",
                                src, dst, cfg, use_cache=False)
                msg = "成功 · %s · %.2fs\n%s" % (res.engine, res.elapsed, res.text)
            except Exception as e:  # noqa: BLE001
                msg = "失败：%s" % e
            self._test_result = msg
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(0, self._show_test_result)

        threading.Thread(target=work, daemon=True).start()

    def _show_test_result(self) -> None:
        msg = getattr(self, "_test_result", "")
        self.lbl_test.setText(msg)
        self.lbl_test.setProperty("state", "error" if msg.startswith("失败") else "ok")
        self.lbl_test.style().unpolish(self.lbl_test)
        self.lbl_test.style().polish(self.lbl_test)
        self.btn_test.setEnabled(True)

    def _collect_translate_cfg(self) -> Dict:
        cfg = dict(self._cfg.section("translate"))
        cfg.update({
            "engine": self.cmb_engine.currentData(),
            "source": self.cmb_src.currentData(),
            "target": self.cmb_dst.currentData(),
            "fallback": self.chk_fallback.isChecked(),
            "timeout": self.sp_timeout.value(),
            "google": cfg.get("google") or {},
            "llm": {
                "base_url": self.ed_llm_url.text().strip(),
                "api_key": self.ed_llm_key.text().strip(),
                "model": self.ed_llm_model.text().strip(),
                "temperature": (cfg.get("llm") or {}).get("temperature", 0.2),
                "prompt": self.txt_llm_prompt.toPlainText().strip(),
            },
            "baidu": {"appid": self.ed_bd_appid.text().strip(),
                      "key": self.ed_bd_key.text().strip()},
            "youdao_official": {"appkey": self.ed_yd_appkey.text().strip(),
                                "secret": self.ed_yd_secret.text().strip()},
            "custom": {
                "url": self.ed_cu_url.text().strip(),
                "method": self.ed_cu_method.currentText(),
                "headers": self.ed_cu_headers.text().strip() or "{}",
                "body": self.ed_cu_body.text().strip(),
                "result_path": self.ed_cu_path.text().strip(),
            },
        })
        return cfg

    # ------------------------------------------------------------ 外观页

    def _tab_ui(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(10, 12, 10, 10)
        root.setSpacing(12)

        self.sp_font = QSpinBox()
        self.sp_font.setRange(9, 22)
        self.sp_font.setSuffix(" px")

        self.sp_width = QSpinBox()
        self.sp_width.setRange(360, 1000)
        self.sp_width.setSingleStep(20)
        self.sp_width.setSuffix(" px")

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("深色（推荐）", "dark")
        self.cmb_theme.addItem("浅色", "light")

        self.chk_ontop = QCheckBox("结果窗口始终置顶")
        self.chk_autocopy = QCheckBox("翻译完成后自动复制译文")
        self.chk_showsrc = QCheckBox("显示原文区域")
        self.chk_magnifier = QCheckBox("框选时显示放大镜")
        self.chk_hint = QCheckBox("框选时显示操作提示")

        root.addWidget(_group("结果窗口", _form([
            ("字号", self.sp_font),
            ("窗口宽度", self.sp_width),
            ("主题", self.cmb_theme),
            ("", self.chk_ontop),
            ("", self.chk_autocopy),
            ("", self.chk_showsrc),
        ])))

        root.addWidget(_group("框选界面", _form([
            ("", self.chk_magnifier),
            ("", self.chk_hint),
        ])))
        root.addStretch(1)
        return page

    # ------------------------------------------------------------ 系统页

    def _tab_system(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(10, 12, 10, 10)
        root.setSpacing(12)

        self.chk_autostart = QCheckBox("开机自动启动（写入注册表 Run 项）")
        self.chk_notify = QCheckBox("出错时显示系统通知")

        self.sp_cache = QSpinBox()
        self.sp_cache.setRange(10, 5000)
        self.sp_cache.setSuffix(" 条")

        root.addWidget(_group("启动与提示", _form([
            ("", self.chk_autostart),
            ("", self.chk_notify),
            ("翻译缓存", self.sp_cache),
        ])))

        btn_sc = QPushButton("创建桌面快捷方式")
        btn_sc.clicked.connect(self._create_shortcut)
        btn_sm = QPushButton("创建开始菜单快捷方式")
        btn_sm.clicked.connect(lambda: self._create_shortcut(start_menu=True))
        btn_dir = QPushButton("打开配置目录")
        btn_dir.clicked.connect(lambda: self._open(paths.config_dir()))
        btn_clr = QPushButton("清空翻译缓存")
        btn_clr.clicked.connect(self._clear_cache)

        row = QHBoxLayout()
        for b in (btn_sc, btn_sm, btn_dir, btn_clr):
            row.addWidget(b)
        row.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(row)

        self.lbl_sysmsg = _label("")
        root.addWidget(_group("快捷方式与数据", _form([
            ("", wrap), ("", self.lbl_sysmsg),
        ])))

        info = (
            "版本：%s\n程序目录：%s\n配置文件：%s\n资源目录：%s\n运行方式：%s"
            % (paths.APP_VERSION, paths.app_dir(), paths.config_path(),
               paths.resource_dir(), "打包程序" if paths.is_frozen() else "Python 源码")
        )
        root.addWidget(_group("关于", _label(info)))
        root.addStretch(1)
        return page

    # ------------------------------------------------------------ 行为

    def _create_shortcut(self, start_menu: bool = False) -> None:
        directory = shortcut.start_menu_dir() if start_menu else None
        ok, msg = shortcut.create_shortcut(directory)
        self.lbl_sysmsg.setText(("✓ " if ok else "✗ ") + msg)

    def _open(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # noqa: S606
        except Exception as e:  # noqa: BLE001
            self.lbl_sysmsg.setText("打开失败：%s" % e)

    def _clear_cache(self) -> None:
        from .translate import clear_cache

        clear_cache()
        self.lbl_sysmsg.setText("✓ 翻译缓存已清空")

    # ------------------------------------------------------------ 载入 / 保存

    def _load(self) -> None:
        ui = self._cfg.section("ui")
        ocr = self._cfg.section("ocr")
        tr = self._cfg.section("translate")
        be = self._cfg.section("behavior")

        self._select(self.cmb_hkmode, self._cfg.get("hotkeys.mode", "auto"))
        self._select(self.cmb_ocr, ocr.get("engine", "auto"))
        self._select(self.cmb_ocr_lang, ocr.get("lang", "ch"))
        self.sp_upscale.setValue(float(ocr.get("upscale", 2.0) or 1.0))
        self.sp_threshold.setValue(int(ocr.get("upscale_threshold", 900) or 900))
        self.chk_enhance.setChecked(bool(ocr.get("enhance", True)))
        self.chk_angle.setChecked(bool(ocr.get("use_angle_cls", True)))
        self.chk_merge.setChecked(bool(ocr.get("merge_lines", True)))
        self.sp_score.setValue(float(ocr.get("text_score", 0.5) or 0.0))

        self._select(self.cmb_engine, tr.get("engine", "auto"))
        self._select(self.cmb_src, tr.get("source", "auto"))
        self._select(self.cmb_dst, tr.get("target", "zh-CHS"))
        self.chk_fallback.setChecked(bool(tr.get("fallback", True)))
        self.sp_timeout.setValue(int(tr.get("timeout", 12) or 12))

        self.sp_font.setValue(int(ui.get("font_size", 12) or 12))
        self.sp_width.setValue(int(ui.get("result_width", 560) or 560))
        self._select(self.cmb_theme, ui.get("theme", "dark"))
        self.chk_ontop.setChecked(bool(ui.get("always_on_top", True)))
        self.chk_autocopy.setChecked(bool(ui.get("auto_copy", False)))
        self.chk_showsrc.setChecked(bool(ui.get("show_original", True)))
        self.chk_magnifier.setChecked(bool(ui.get("magnifier", True)))
        self.chk_hint.setChecked(bool(ui.get("overlay_hint", True)))

        self.chk_autostart.setChecked(paths.is_autostart_enabled())
        self.chk_notify.setChecked(bool(be.get("notify", True)))
        self.sp_cache.setValue(int(be.get("cache_size", 300) or 300))

        self._refresh_hotkey_status()

    def _refresh_hotkey_status(self) -> None:
        if self._ctx is None:
            self.lbl_hk_status.setText("（未连接运行实例）")
            return
        conflicts = getattr(self._ctx, "hotkey_conflicts", {})
        backend = getattr(self._ctx, "hotkey_backend", "")
        lines = ["注册方式：%s" % (backend or "未知")]
        if conflicts:
            lines.append("以下快捷键未能生效：")
            for action, reason in conflicts.items():
                lines.append("  · %s：%s" % (action, reason))
        else:
            lines.append("所有快捷键均已生效。")
        self.lbl_hk_status.setText("\n".join(lines))

    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _reset(self) -> None:
        ok = QMessageBox.question(self, "恢复默认", "确定要把所有设置恢复为默认值吗？",
                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ok == QMessageBox.Yes:
            self._cfg.reset()
            self._load()
            self.saved.emit()

    def _save(self) -> None:
        cfg = self._cfg
        mode = self.cmb_hkmode.currentData()

        cfg.set("hotkeys.capture", self.ed_capture.text().strip(), autosave=False)
        cfg.set("hotkeys.clipboard", self.ed_clipboard.text().strip(), autosave=False)
        cfg.set("hotkeys.repeat", self.ed_repeat.text().strip(), autosave=False)
        cfg.set("hotkeys.mode", mode, autosave=False)

        cfg.set("ocr.engine", self.cmb_ocr.currentData(), autosave=False)
        cfg.set("ocr.lang", self.cmb_ocr_lang.currentData(), autosave=False)
        cfg.set("ocr.upscale", self.sp_upscale.value(), autosave=False)
        cfg.set("ocr.upscale_threshold", self.sp_threshold.value(), autosave=False)
        cfg.set("ocr.enhance", self.chk_enhance.isChecked(), autosave=False)
        cfg.set("ocr.use_angle_cls", self.chk_angle.isChecked(), autosave=False)
        cfg.set("ocr.merge_lines", self.chk_merge.isChecked(), autosave=False)
        cfg.set("ocr.text_score", self.sp_score.value(), autosave=False)

        tcfg = self._collect_translate_cfg()
        for key, value in tcfg.items():
            cfg.set("translate.%s" % key, value, autosave=False)

        cfg.set("ui.font_size", self.sp_font.value(), autosave=False)
        cfg.set("ui.result_width", self.sp_width.value(), autosave=False)
        cfg.set("ui.theme", self.cmb_theme.currentData(), autosave=False)
        cfg.set("ui.always_on_top", self.chk_ontop.isChecked(), autosave=False)
        cfg.set("ui.auto_copy", self.chk_autocopy.isChecked(), autosave=False)
        cfg.set("ui.show_original", self.chk_showsrc.isChecked(), autosave=False)
        cfg.set("ui.magnifier", self.chk_magnifier.isChecked(), autosave=False)
        cfg.set("ui.overlay_hint", self.chk_hint.isChecked(), autosave=False)

        cfg.set("behavior.notify", self.chk_notify.isChecked(), autosave=False)
        cfg.set("behavior.cache_size", self.sp_cache.value(), autosave=False)

        paths.set_autostart(self.chk_autostart.isChecked())
        cfg.save()

        from .translate import set_cache_size

        set_cache_size(self.sp_cache.value())

        self.saved.emit()
        self.accept()
