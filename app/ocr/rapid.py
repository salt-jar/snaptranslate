# -*- coding: utf-8 -*-
"""RapidOCR（PP-OCR ONNX 版）离线识别引擎 —— 主力引擎。

完全离线、免费，中英混排效果好，模型随 wheel 一起安装。
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..paths import app_dir
from .base import OcrResult, TextBox, filter_boxes, lines_to_text, merge_into_lines
from .preprocess import prepare_png


def _find_models(lang: str) -> Dict[str, str]:
    """在 ``models/<lang>/`` 下查找自定义模型（可选，用于中英以外的语种）。"""
    if not lang or lang == "ch":
        return {}
    root = app_dir() / "models" / lang
    if not root.is_dir():
        return {}
    out: Dict[str, str] = {}
    for key, patterns in (
        ("det_model_path", ("det.onnx", "*det*.onnx")),
        ("rec_model_path", ("rec.onnx", "*rec*.onnx")),
        ("cls_model_path", ("cls.onnx", "*cls*.onnx")),
    ):
        for pat in patterns:
            hits = sorted(root.glob(pat))
            if hits:
                out[key] = str(hits[0])
                break
    return out


class RapidOcrEngine:
    key = "rapidocr"
    label = "RapidOCR 离线识别"
    detail = "本地运行，免费无限制，中英混排效果最好"

    _lock = threading.Lock()
    _engine: Any = None
    _engine_key: str = ""
    _input_kind: str = ""      # bytes / ndarray / path，首次调用时自动探测

    def __init__(self, cfg: dict):
        self._cfg = dict(cfg or {})

    # ---------------------------------------------------------------- 可用性

    @classmethod
    def available(cls) -> bool:
        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401
            import onnxruntime  # noqa: F401
            import rapidocr_onnxruntime  # noqa: F401

            return True
        except Exception:
            return False

    @classmethod
    def unavailable_reason(cls) -> str:
        missing = []
        for mod, pkg in (("onnxruntime", "onnxruntime"), ("cv2", "opencv-python-headless"),
                         ("rapidocr_onnxruntime", "rapidocr-onnxruntime")):
            try:
                __import__(mod)
            except Exception:
                missing.append(pkg)
        if missing:
            return "缺少依赖：%s（运行 安装依赖.bat 或 pip install %s）" % (
                "、".join(missing), " ".join(missing))
        return ""

    # ---------------------------------------------------------------- 引擎实例

    def _get_engine(self):
        lang = str(self._cfg.get("lang") or "ch")
        with RapidOcrEngine._lock:
            if RapidOcrEngine._engine is not None and RapidOcrEngine._engine_key == lang:
                return RapidOcrEngine._engine

            from rapidocr_onnxruntime import RapidOCR

            kwargs: Dict[str, Any] = {}
            kwargs.update(_find_models(lang))
            # 不同小版本参数名有差异，逐个降级尝试
            for extra in (
                {"use_cls": bool(self._cfg.get("use_angle_cls", True))},
                {"use_angle_cls": bool(self._cfg.get("use_angle_cls", True))},
                {},
            ):
                try:
                    RapidOcrEngine._engine = RapidOCR(**kwargs, **extra)
                    break
                except TypeError:
                    continue
            if RapidOcrEngine._engine is None:
                RapidOcrEngine._engine = RapidOCR()
            RapidOcrEngine._engine_key = lang
            RapidOcrEngine._input_kind = ""
            return RapidOcrEngine._engine

    # ---------------------------------------------------------------- 识别

    def _invoke(self, engine, png: bytes, ndarray):
        """不同版本的 RapidOCR 接受的输入类型不一样，按优先级探测一次后记住。"""
        kind = RapidOcrEngine._input_kind
        trials: List[str] = []
        if kind:
            trials.append(kind)
        trials += [k for k in ("bytes", "ndarray", "path") if k != kind]

        last_err: Optional[Exception] = None
        for k in trials:
            try:
                if k == "bytes":
                    out = engine(png)
                elif k == "ndarray":
                    import cv2
                    import numpy as np

                    out = engine(cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR))
                else:
                    from ..paths import cache_dir

                    p = cache_dir() / "rapid_input.png"
                    p.write_bytes(png)
                    out = engine(str(p))
                RapidOcrEngine._input_kind = k
                return out
            except Exception as e:  # noqa: BLE001
                last_err = e
                continue
        if last_err:
            raise last_err
        return None, None

    def recognize(self, qimg) -> OcrResult:
        cfg = self._cfg
        t0 = time.perf_counter()
        png, scale = prepare_png(
            qimg,
            upscale=float(cfg.get("upscale", 2.0) or 1.0),
            threshold=int(cfg.get("upscale_threshold", 900) or 900),
            enhance=bool(cfg.get("enhance", True)),
        )
        if not png:
            return OcrResult("", [], self.key, time.perf_counter() - t0,
                             qimg.width(), qimg.height())

        engine = self._get_engine()
        out = self._invoke(engine, png, None)

        if isinstance(out, tuple):
            raw, _elapse = (out + (None,))[:2] if len(out) < 2 else out[:2]
        else:
            raw = out

        boxes: List[TextBox] = []
        for item in raw or []:
            try:
                poly, text = item[0], item[1]
                score = float(item[2]) if len(item) > 2 else 1.0
            except Exception:
                continue
            if not text:
                continue
            box = TextBox.from_polygon(poly, str(text), score)
            if scale and scale > 1.0:      # 坐标还原到原图尺度
                box = TextBox(box.x0 / scale, box.y0 / scale, box.x1 / scale,
                              box.y1 / scale, box.text, box.score)
            boxes.append(box)

        boxes = filter_boxes(boxes, float(cfg.get("text_score", 0.5) or 0.0))
        if cfg.get("merge_lines", True):
            lines = merge_into_lines(boxes, float(cfg.get("line_tolerance", 0.6)))
        else:
            lines = [[b] for b in sorted(boxes, key=lambda b: (b.cy, b.x0))]
        text = lines_to_text(lines)

        return OcrResult(text, boxes, self.key, time.perf_counter() - t0,
                         qimg.width(), qimg.height())
