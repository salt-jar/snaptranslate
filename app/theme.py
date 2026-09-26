# -*- coding: utf-8 -*-
"""界面主题：深色 / 浅色两套样式表与配色。"""
from __future__ import annotations

from typing import Dict

DARK: Dict[str, str] = {
    "bg": "#1b1d22",
    "bg_alt": "#23262d",
    "bg_elev": "#2a2e36",
    "border": "#3a3f4a",
    "text": "#e8eaed",
    "text_dim": "#9aa0ab",
    "accent": "#4c8dff",
    "accent_hover": "#669dff",
    "accent_text": "#ffffff",
    "ok": "#4ec97a",
    "warn": "#e9b949",
    "error": "#f0685a",
    "sel": "#2f4f86",
}

LIGHT: Dict[str, str] = {
    "bg": "#f6f7f9",
    "bg_alt": "#ffffff",
    "bg_elev": "#ffffff",
    "border": "#d7dae0",
    "text": "#1f2329",
    "text_dim": "#6b7280",
    "accent": "#2f6ff5",
    "accent_hover": "#1f5ce0",
    "accent_text": "#ffffff",
    "ok": "#1f9d55",
    "warn": "#b7791f",
    "error": "#d9483b",
    "sel": "#cfe0ff",
}


def palette(theme: str = "dark") -> Dict[str, str]:
    return DARK if theme == "dark" else LIGHT


def stylesheet(theme: str = "dark", font_size: int = 12) -> str:
    c = palette(theme)
    return """
* {{ font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif; }}

QWidget {{
    color: {text};
    font-size: {fs}px;
}}

QMainWindow, QDialog, #Root {{
    background: {bg};
}}

#Card {{
    background: {bg_alt};
    border: 1px solid {border};
    border-radius: 12px;
}}

#TitleBar {{
    background: transparent;
}}

#TitleLabel {{
    font-size: {fs_title}px;
    font-weight: 600;
    color: {text};
}}

QLabel[role="hint"] {{
    color: {text_dim};
    font-size: {fs_small}px;
}}

QLabel[role="section"] {{
    color: {text_dim};
    font-size: {fs_small}px;
    font-weight: 600;
    padding: 2px 0;
}}

QPushButton {{
    background: {bg_elev};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 14px;
    color: {text};
}}
QPushButton:hover   {{ background: {border}; }}
QPushButton:pressed {{ background: {bg}; }}
QPushButton:disabled {{ color: {text_dim}; background: {bg}; }}

QPushButton[accent="true"] {{
    background: {accent};
    border: 1px solid {accent};
    color: {accent_text};
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}

QPushButton[flat="true"] {{
    background: transparent;
    border: 1px solid transparent;
    padding: 4px 8px;
    color: {text_dim};
}}
QPushButton[flat="true"]:hover {{ background: {bg_elev}; color: {text}; }}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
    color: {text_dim};
}}
QToolButton:hover {{ background: {bg_elev}; color: {text}; }}
QToolButton:checked {{ background: {accent}; color: {accent_text}; }}

QTextEdit, QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {sel};
    selection-color: {text};
}}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {accent};
}}
QTextEdit[readOnly="true"] {{ background: {bg_alt}; }}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {bg_elev};
    border: 1px solid {border};
    selection-background-color: {sel};
    outline: none;
}}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}

QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 10px;
    background: {bg_alt};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {text_dim};
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    background: {bg_alt};
    color: {text};
    border: 1px solid {border};
    border-bottom-color: {bg_alt};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {text}; }}

QGroupBox {{
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {text_dim};
}}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {border}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {text_dim}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 30px; }}

QMenu {{
    background: {bg_elev};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 6px;
}}
QMenu::item:selected {{ background: {accent}; color: {accent_text}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}

QStatusBar {{ background: transparent; color: {text_dim}; }}

QSplitter::handle {{ background: {border}; height: 1px; }}

QToolTip {{
    background: {bg_elev};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 8px;
}}

#HotkeyEdit {{
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: {fs_title}px;
    font-weight: 600;
    color: {accent};
    letter-spacing: 1px;
}}

#TransView {{
    background: {bg_alt};
    border: 1px solid {border};
    border-radius: 10px;
    font-size: {fs_trans}px;
    line-height: 165%;
}}

#SourceView {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 10px;
    color: {text_dim};
}}

#StatusLabel {{ color: {text_dim}; font-size: {fs_small}px; }}
#StatusLabel[state="error"] {{ color: {error}; }}
#StatusLabel[state="ok"] {{ color: {ok}; }}
""".format(
        fs=font_size,
        fs_small=max(9, font_size - 2),
        fs_title=font_size + 1,
        fs_trans=font_size + 3,
        **c,
    )
