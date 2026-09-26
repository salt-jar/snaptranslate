# -*- coding: utf-8 -*-
"""配置的读写、默认值与点号路径访问。"""
from __future__ import annotations

import copy
import json
import threading
from typing import Any, Dict

from . import paths

DEFAULTS: Dict[str, Any] = {
    "hotkeys": {
        # 快捷键字符串格式：Ctrl+Alt+Z ；支持 Ctrl / Alt / Shift / Win 与 A-Z 0-9 F1-F24
        "capture": "Ctrl+Alt+Z",
        "clipboard": "Ctrl+Alt+X",
        "repeat": "Ctrl+Alt+C",
        "toggle_window": "",
        "enabled": True,
        # auto=先尝试系统注册，被占用时退回键盘钩子; native=仅系统注册; listener=仅钩子
        "mode": "auto",
    },
    "ocr": {
        "engine": "auto",          # auto / rapidocr / winocr / tesseract
        "lang": "ch",              # rapidocr 语言包标识
        "upscale": 2.0,            # 小图放大倍数，显著提升小字识别率
        "upscale_threshold": 900,  # 图像最长边小于该值才放大
        "enhance": True,           # 灰度 + 自动对比度
        "text_score": 0.5,         # 置信度阈值
        "use_angle_cls": True,     # 方向分类（处理翻转文字）
        "merge_lines": True,       # 按行归并、保持阅读顺序
        "line_tolerance": 0.6,
    },
    "translate": {
        "engine": "youdao_free",   # 见 translate/ 里的引擎注册表
        "source": "auto",
        "target": "auto",          # auto = 中文原文译英文，其它语言译中文
        "fallback": True,          # 主引擎失败时自动换备用引擎
        "timeout": 12,
        "max_chunk": 1400,         # 单次请求最大字符数，超出自动分段
        # 术语表：每行一条，支持 `源=译`、`源=>译`、`源→译`；只写一个词表示保持原样。
        # 例：["GPU=GPU", "量化=quantization", "ONNX Runtime=ONNX Runtime"]
        "glossary": [],
        "llm": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
            "temperature": 0.2,
            "prompt": (
                "你是一个专业翻译引擎。把用户给出的文本翻译成{target}。"
                "要求：只输出译文本身，不要任何解释、前后缀或引号；"
                "保持原文的换行与段落结构；专有名词保留原文；"
                "如果原文已经是{target}，原样返回。"
            ),
        },
        "baidu": {"appid": "", "key": ""},
        "youdao_official": {"appkey": "", "secret": ""},
        "local": {
            "device": "cpu",          # cpu / cuda
            "compute_type": "int8",   # int8 最快且内存占用小；auto / float32 亦可
            "beam_size": 1,           # 1 最快，调大质量略好但明显变慢
        },
        "custom": {
            "url": "",
            "method": "POST",
            "headers": '{"Content-Type": "application/json"}',
            "body": '{"text": "{text}", "from": "{from}", "to": "{to}"}',
            "result_path": "data.translation",
        },
        "google": {"base_url": "https://translate.googleapis.com"},
    },
    "ui": {
        "font_size": 12,
        "result_width": 560,
        "always_on_top": True,
        "auto_copy": False,
        "show_original": True,
        "theme": "dark",           # dark / light
        "overlay_hint": True,
        "magnifier": True,
    },
    "behavior": {
        "start_minimized": True,
        "notify": True,
        "cache_size": 300,
        "keep_history": 20,
        "history": [],
        "last_region": None,       # [x, y, w, h] 逻辑像素
        "seen_welcome": False,
    },
}


class Config:
    """线程安全的配置对象，支持 cfg.get('a.b.c') 与 cfg.set(...) 自动落盘。"""

    def __init__(self, path=None):
        self._lock = threading.RLock()
        self.path = path or paths.config_path()
        self.data: Dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # ---------------------------------------------------------------- 读写

    def load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._merge(self.data, raw)
        except Exception:
            pass  # 配置损坏时静默使用默认值，避免程序无法启动

    @staticmethod
    def _merge(base: dict, incoming: dict) -> None:
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                Config._merge(base[k], v)
            else:
                base[k] = v

    def save(self) -> bool:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".json.tmp")
                tmp.write_text(
                    json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                tmp.replace(self.path)
                return True
            except Exception:
                return False

    def reset(self) -> None:
        with self._lock:
            self.data = copy.deepcopy(DEFAULTS)
        self.save()

    # ---------------------------------------------------------------- 访问

    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set(self, dotted: str, value: Any, autosave: bool = True) -> None:
        with self._lock:
            parts = dotted.split(".")
            cur = self.data
            for part in parts[:-1]:
                nxt = cur.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[part] = nxt
                cur = nxt
            cur[parts[-1]] = value
        if autosave:
            self.save()

    def section(self, name: str) -> Dict[str, Any]:
        v = self.data.get(name)
        return v if isinstance(v, dict) else {}


config = Config()
