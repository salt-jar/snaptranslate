# -*- coding: utf-8 -*-
"""OCR 引擎注册表与自动选择。"""
from __future__ import annotations

from typing import Dict, List, Tuple, Type

from .base import OcrResult, TextBox
from .rapid import RapidOcrEngine
from .tesseract import TesseractEngine
from .winocr import WinOcrEngine

# 顺序即自动选择的优先级：优先本地效果好、其次零依赖
ENGINES: List[Type] = [RapidOcrEngine, WinOcrEngine, TesseractEngine]
_BY_KEY: Dict[str, Type] = {e.key: e for e in ENGINES}

__all__ = ["OcrResult", "TextBox", "ENGINES", "get_engine", "list_engines",
           "auto_engine_key", "engine_status", "warmup"]


#: 需要预热的原生扩展模块
_WARMUP = ("numpy", "cv2", "onnxruntime", "rapidocr_onnxruntime",
           "pyclipper", "shapely", "yaml",
           # 离线翻译引擎。ctranslate2 必须在 sentencepiece 之前：
           # 实测 ctranslate2 -> Qt -> sentencepiece 不会崩，
           # 而 Qt -> sentencepiece 会直接 0xC0000005 访问违例。
           "ctranslate2", "sentencepiece")

_warmed = False


def warmup() -> None:
    """提前导入依赖原生 DLL 的模块。

    **必须在创建 QApplication 之前调用。** 实测（Windows + PyQt5 5.15）：

    * Qt 初始化之后再 ``import onnxruntime`` →
      ``ImportError: DLL load failed while importing onnxruntime_pybind11_state:
      动态链接库(DLL)初始化例程失败``
    * Qt 初始化之后再 ``import sentencepiece`` →
      **整个进程直接崩溃**（退出码 0xC0000005，访问违例）

    先导入则一切正常，且不影响之后创建 Qt 应用。导入失败会被忽略，
    这样缺少某个可选依赖时程序仍能启动，只是该引擎显示为不可用。
    """
    global _warmed
    if _warmed:
        return
    from .. import startup_log

    for mod in _WARMUP:
        startup_log.log("warmup: 正在导入 %s" % mod)
        try:
            __import__(mod)
            startup_log.log("warmup: %s OK" % mod)
        except Exception as e:  # noqa: BLE001
            startup_log.log("warmup: %s 失败 %s: %s"
                            % (mod, type(e).__name__, str(e).replace("\n", " ")[:200]))
    _warmed = True
    startup_log.log("warmup: 完成")


def list_engines() -> List[Tuple[str, str]]:
    """返回 [(key, 显示名), ...]，含 auto。"""
    out = [("auto", "自动选择（推荐）")]
    for e in ENGINES:
        out.append((e.key, e.label))
    return out


def engine_status() -> Dict[str, str]:
    """返回 {key: 状态说明}，用于设置界面。"""
    st: Dict[str, str] = {}
    for e in ENGINES:
        try:
            ok = e.available()
        except Exception:
            ok = False
        st[e.key] = "可用" if ok else e.unavailable_reason()
    return st


def auto_engine_key() -> str:
    for e in ENGINES:
        try:
            if e.available():
                return e.key
        except Exception:
            continue
    return ""


def get_engine(name: str, cfg: dict):
    """按名称取引擎实例；``auto`` 或不可用时自动降级。"""
    cfg = dict(cfg or {})
    key = (name or "auto").strip()
    if key == "auto":
        key = auto_engine_key()
        if not key:
            raise RuntimeError(
                "没有可用的 OCR 引擎。请运行「安装依赖.bat」安装 RapidOCR，"
                "或在设置里启用 Windows 自带 OCR。"
            )
    cls = _BY_KEY.get(key)
    if cls is None:
        raise RuntimeError("未知的 OCR 引擎：%s" % key)
    if not cls.available():
        raise RuntimeError("%s 当前不可用：%s" % (cls.label, cls.unavailable_reason()))
    return cls(cfg)
