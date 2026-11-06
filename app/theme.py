# -*- coding: utf-8 -*-
"""界面主题：iOS 风格配色与样式表（浅色 / 深色）。"""
from __future__ import annotations

from typing import Dict

from . import paths

# --------------------------------------------------------------------------- 配色
#
# 取色参考 iOS 系统色：
#   背景 systemGroupedBackground / 卡片 secondarySystemGroupedBackground /
#   控件填充 tertiarySystemFill / 强调色 systemBlue / 开关 systemGreen。
# 深色沿用 iOS 的纯黑画布 + #1C1C1E 卡片层级。

LIGHT: Dict[str, str] = {
    "bg": "#F2F2F7",
    "bg_alt": "#FFFFFF",
    "bg_elev": "#FFFFFF",
    "fill": "#F2F2F7",
    "fill_hover": "#EAEAF0",
    "fill_pressed": "#E1E1E8",
    "border": "#E5E5EA",
    "separator": "#E7E7EC",
    "text": "#000000",
    "text_dim": "#8A8A8E",
    "text_soft": "#636366",
    "accent": "#007AFF",
    "accent_hover": "#0066D6",
    "accent_text": "#FFFFFF",
    "accent_soft": "#E5F0FF",
    "ok": "#34C759",
    "warn": "#FF9500",
    "error": "#FF3B30",
    "sel": "#D6E4FF",
    "switch_off": "#E9E9EA",
    "segment_on": "#FFFFFF",
    "segment_border": "#E3E3E8",
    "scroll": "#C7C7CC",
}

DARK: Dict[str, str] = {
    "bg": "#000000",
    "bg_alt": "#1C1C1E",
    "bg_elev": "#2C2C2E",
    "fill": "#2C2C2E",
    "fill_hover": "#3A3A3C",
    "fill_pressed": "#48484A",
    "border": "#38383A",
    "separator": "#38383A",
    "text": "#FFFFFF",
    "text_dim": "#98989F",
    "text_soft": "#AEAEB2",
    "accent": "#0A84FF",
    "accent_hover": "#409CFF",
    "accent_text": "#FFFFFF",
    "accent_soft": "#0B2B4D",
    "ok": "#30D158",
    "warn": "#FF9F0A",
    "error": "#FF453A",
    "sel": "#0A3A6E",
    "switch_off": "#39393D",
    "segment_on": "#48484A",
    "segment_border": "#5A5A5E",
    "scroll": "#48484A",
}


def palette(theme: str = "light") -> Dict[str, str]:
    return LIGHT if theme != "dark" else DARK


def current_palette() -> Dict[str, str]:
    """当前生效的配色：由 :func:`apply` 写入 QApplication 属性。"""
    try:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            p = app.property("ios_palette")
            if isinstance(p, dict) and p:
                return p
    except Exception:
        pass
    return LIGHT


def _asset(name: str) -> str:
    try:
        return (paths.resource_dir() / "resources" / name).as_posix()
    except Exception:
        return ""


def apply(app, theme: str = "light", font_size: int = 13) -> None:
    """把主题、字体、配色一次性应用到 QApplication。

    自定义绘制的控件（iOS 开关、活动指示器）从 ``ios_palette`` 属性取色，
    因此这里必须先把属性写进去，再设置样式表。
    """
    from PyQt5.QtGui import QFont

    theme = "dark" if theme == "dark" else "light"
    colors = palette(theme)
    app.setProperty("ios_palette", dict(colors))
    app.setProperty("ios_theme", theme)

    try:
        if app.style().objectName().lower() != "fusion":
            app.setStyle("Fusion")
    except Exception:
        pass

    font = QFont()
    try:
        font.setFamilies([
            "SF Pro Text", "SF Pro Display", "Segoe UI Variable Text",
            "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei",
        ])
    except Exception:
        font.setFamily("Segoe UI")
    font.setPixelSize(max(9, int(font_size)))
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(stylesheet(theme, font_size))


# --------------------------------------------------------------------------- 样式表


def stylesheet(theme: str = "light", font_size: int = 13) -> str:
    c = dict(palette(theme))
    c["chevron"] = _asset("chevron-down.png")
    c["check"] = _asset("check.png")
    fs = int(font_size)
    return """
/* ---------------------------------------------------------------- 基础 */
* {{
    outline: none;
}}

QWidget {{
    color: {text};
    font-size: {fs}px;
}}

QMainWindow, QDialog, #Root {{
    background: {bg};
}}

QDialog#CardDialog {{
    background: transparent;
}}

QFrame#WindowCard {{
    background: {bg_alt};
    border: 1px solid {separator};
    border-radius: 20px;
}}

QFrame#Card {{
    background: {bg_alt};
    border: 1px solid {separator};
    border-radius: 18px;
}}

QFrame#GroupCard {{
    background: {bg_alt};
    border: 1px solid {separator};
    border-radius: 14px;
}}

QFrame#SegmentedTrack {{
    background: {fill};
    border: 1px solid {separator};
    border-radius: 11px;
}}

QFrame[role="separator"] {{
    background: {separator};
    border: none;
    min-height: 1px;
    max-height: 1px;
}}

#TitleBar, #DialogHeader {{
    background: transparent;
}}

#TitleLabel {{
    font-size: {fs_title}px;
    font-weight: 600;
    color: {text};
}}

#SubtitleLabel {{
    color: {text_dim};
    font-size: {fs_small}px;
}}

#Badge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #4C8DFF, stop:1 #7C5CFF);
    color: #FFFFFF;
    border-radius: 7px;
    font-weight: 700;
    font-size: {fs_badge}px;
}}

#BadgeLarge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #4C8DFF, stop:1 #7C5CFF);
    color: #FFFFFF;
    border-radius: 10px;
    font-weight: 700;
    font-size: {fs_title}px;
}}

/* ---------------------------------------------------------------- 文字 */
QLabel[role="section"] {{
    color: {text_dim};
    font-size: {fs_small}px;
    font-weight: 600;
    padding-left: 4px;
}}

QLabel[role="hint"] {{
    color: {text_dim};
    font-size: {fs_small}px;
}}

QLabel[role="row"] {{
    color: {text};
    font-size: {fs}px;
}}

QLabel[role="mono"], QLabel#AboutInfo {{
    color: {text_dim};
    font-size: {fs_small}px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}}

QLabel[role="error"] {{ color: {error}; }}
QLabel[role="ok"] {{ color: {ok}; }}

#StatusLabel {{
    color: {text_dim};
    font-size: {fs_small}px;
}}
#StatusLabel[state="error"] {{ color: {error}; }}
#StatusLabel[state="ok"] {{ color: {text_dim}; }}
#StatusLabel[state="busy"] {{ color: {text_dim}; }}

/* ---------------------------------------------------------------- 按钮 */
QPushButton {{
    background: {fill};
    color: {accent};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 7px 16px;
    min-height: 20px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {fill_hover};
}}
QPushButton:pressed {{
    background: {fill_pressed};
}}
QPushButton:disabled {{
    color: {text_dim};
    background: {fill};
}}
QPushButton:focus {{
    border: 1px solid {accent};
}}

QPushButton[accent="true"] {{
    background: {accent};
    color: {accent_text};
    border: 1px solid {accent};
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{
    background: {accent_hover};
    border-color: {accent_hover};
}}
QPushButton[accent="true"]:pressed {{
    background: {accent_hover};
}}
QPushButton[accent="true"]:focus {{
    border: 1px solid {accent_text};
}}
QPushButton[accent="true"]:disabled {{
    background: {fill};
    color: {text_dim};
    border-color: transparent;
}}

QPushButton[flat="true"] {{
    background: transparent;
    color: {accent};
    border: 1px solid transparent;
    padding: 6px 10px;
}}
QPushButton[flat="true"]:hover {{
    background: {fill};
}}
QPushButton[danger="true"] {{
    background: transparent;
    color: {error};
    border: 1px solid transparent;
}}
QPushButton[danger="true"]:hover {{
    background: {fill};
}}
QPushButton[danger="true"]:disabled {{
    color: {text_dim};
    background: transparent;
}}

QPushButton[segment="true"] {{
    background: transparent;
    color: {text};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton[segment="true"]:hover {{
    background: {fill_hover};
}}
QPushButton[segment="true"]:checked {{
    background: {segment_on};
    border: 1px solid {segment_border};
    font-weight: 600;
}}

QToolButton {{
    background: transparent;
    color: {text_dim};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 0;
    min-width: 28px;
    min-height: 28px;
}}
QToolButton:hover {{
    background: {fill};
    color: {text};
}}
QToolButton:pressed {{
    background: {fill_pressed};
}}
QToolButton:checked {{
    background: {accent_soft};
    color: {accent};
    border-color: transparent;
}}
QToolButton[glyph="true"] {{
    font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
    font-size: {fs_icon}px;
}}
QToolButton#SwapButton {{
    font-size: {fs_title}px;
    color: {text_dim};
    border-radius: 14px;
}}

/* ---------------------------------------------------------------- 输入 */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {fill};
    color: {text};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 19px;
    selection-background-color: {sel};
    selection-color: {text};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    background: {fill_hover};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    background: {bg_alt};
    border: 1px solid {accent};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {text_dim};
}}
QLineEdit[echoMode="2"] {{
    font-family: "Cascadia Mono", "Consolas", monospace;
}}

QPlainTextEdit, QTextEdit {{
    background: {bg_alt};
    color: {text};
    border: 1px solid {separator};
    border-radius: 12px;
    padding: 4px;
    selection-background-color: {sel};
    selection-color: {text};
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {accent};
}}
QTextEdit[readOnly="true"] {{
    background: {bg_alt};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: url("{chevron}");
    width: 10px;
    height: 6px;
}}
QComboBox QAbstractItemView {{
    background: {bg_alt};
    color: {text};
    border: 1px solid {separator};
    border-radius: 10px;
    padding: 5px;
    selection-background-color: {sel};
    selection-color: {text};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 3px 10px;
    border-radius: 6px;
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 18px;
}}

QCheckBox {{
    color: {text};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {border};
    background: {bg_alt};
}}
QCheckBox::indicator:hover {{
    border-color: {text_dim};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
    image: url("{check}");
}}
QRadioButton {{
    color: {text};
    spacing: 8px;
}}

#HotkeyEdit {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-weight: 600;
    color: {accent};
    background: {fill};
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 6px 10px;
}}
#HotkeyEdit:focus {{
    background: {bg_alt};
    border: 1px solid {accent};
}}

/* ---------------------------------------------------------------- 文本区 */
#TransView {{
    background: transparent;
    border: none;
    padding: 0;
    font-size: {fs_trans}px;
}}
#SourceView {{
    background: {fill};
    border: none;
    border-radius: 10px;
    padding: 6px;
    color: {text_soft};
}}

/* ---------------------------------------------------------------- 滚动 */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {scroll};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {text_dim};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 2px;
}}
QScrollBar::handle:horizontal {{
    background: {scroll};
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ---------------------------------------------------------------- 菜单 */
QMenu {{
    background: {bg_alt};
    color: {text};
    border: 1px solid {separator};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 26px 7px 12px;
    border-radius: 7px;
}}
QMenu::item:selected {{
    background: {accent};
    color: {accent_text};
}}
QMenu::item:disabled {{
    color: {text_dim};
}}
QMenu::separator {{
    height: 1px;
    background: {separator};
    margin: 5px 8px;
}}

QToolTip {{
    background: {bg_elev};
    color: {text};
    border: 1px solid {separator};
    border-radius: 8px;
    padding: 5px 8px;
}}

/* ---------------------------------------------------------------- 表格 */
QTableWidget, QTableView {{
    background: {bg_alt};
    alternate-background-color: {bg_alt};
    color: {text};
    border: 1px solid {separator};
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: {sel};
    selection-color: {text};
    outline: none;
}}
QHeaderView {{
    background: transparent;
    border: none;
}}
QHeaderView::section {{
    background: transparent;
    color: {text_dim};
    border: none;
    border-bottom: 1px solid {separator};
    padding: 8px 10px;
    font-size: {fs_small}px;
    font-weight: 600;
}}
QTableWidget::item {{
    border-bottom: 1px solid {separator};
    padding: 6px 10px;
}}
QTableWidget::item:selected {{
    background: {sel};
    color: {text};
}}
QTableCornerButton::section {{
    background: transparent;
    border: none;
}}

/* ---------------------------------------------------------------- 进度 */
QProgressBar {{
    background: {fill};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    min-height: 6px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {accent};
    border-radius: 3px;
}}

/* ---------------------------------------------------------------- 其它 */
QGroupBox {{
    background: {bg_alt};
    border: 1px solid {separator};
    border-radius: 14px;
    margin-top: 14px;
    padding: 14px 12px 10px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 4px;
    color: {text_dim};
}}

QStatusBar {{
    background: transparent;
    color: {text_dim};
}}

QMessageBox {{
    background: {bg_alt};
}}
QMessageBox QLabel {{
    color: {text};
}}

QSplitter::handle {{
    background: {separator};
    height: 1px;
}}
""".format(
        fs=fs,
        fs_small=max(9, fs - 2),
        fs_title=fs + 4,
        fs_trans=fs + 3,
        fs_icon=fs + 1,
        fs_badge=max(10, fs - 1),
        **c,
    )
