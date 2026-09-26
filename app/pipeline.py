# -*- coding: utf-8 -*-
"""OCR + 翻译任务流水线。

在后台线程里跑，通过 Qt 信号把结果送回主线程；用「代次」编号丢弃过期结果，
这样用户连续截图时不会出现旧结果盖掉新结果的情况。
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from . import ocr as ocr_pkg
from . import translate as tr_pkg


class Pipeline(QObject):
    """一次「识别 → 翻译」流程。"""

    started = pyqtSignal()
    ocr_done = pyqtSignal(object, float)          # OcrResult, 秒
    finished = pyqtSignal(object, object)         # OcrResult, TranslateResult
    failed = pyqtSignal(str, str)                 # 阶段('ocr'|'translate'), 消息

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._gen = 0
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- 对外

    def cancel(self) -> None:
        with self._lock:
            self._gen += 1

    def has_text(self, text: str) -> bool:
        return bool((text or "").strip())

    def run(self, qimage, src: str, dst: str, engine: str, ocr_engine: str,
            preset_text: Optional[str] = None, reocr: bool = False) -> int:
        """启动一次流水线，返回本次任务的代次编号。"""
        with self._lock:
            self._gen += 1
            gen = self._gen
        self.started.emit()
        t = threading.Thread(
            target=self._work,
            args=(gen, qimage, src, dst, engine, ocr_engine, preset_text, reocr),
            name="pipeline",
            daemon=True,
        )
        t.start()
        return gen

    def run_text_only(self, text: str, src: str, dst: str, engine: str) -> int:
        """只翻译（剪贴板翻译 / 换引擎重译）。"""
        return self.run(None, src, dst, engine, "auto", preset_text=text, reocr=True)

    # ---------------------------------------------------------------- 内部

    def _alive(self, gen: int) -> bool:
        with self._lock:
            return gen == self._gen

    def _work(self, gen, qimage, src, dst, engine, ocr_engine, preset_text, reocr) -> None:
        ocr_cfg = dict(self._cfg.section("ocr"))
        tcfg = dict(self._cfg.section("translate"))

        # ---- 1. 识别 ----
        ocr_result = None
        if preset_text is None:
            try:
                t0 = time.perf_counter()
                engine_obj = ocr_pkg.get_engine(ocr_engine, ocr_cfg)
                ocr_result = engine_obj.recognize(qimage)
                elapsed = time.perf_counter() - t0
                if not self._alive(gen):
                    return
                self.ocr_done.emit(ocr_result, elapsed)
            except Exception as e:  # noqa: BLE001
                if self._alive(gen):
                    self.failed.emit("ocr", "%s" % (str(e) or type(e).__name__))
                return
            text = ocr_result.text
            if not text.strip():
                if self._alive(gen):
                    self.failed.emit("ocr", "没有识别到文字。可以试试把区域框大一点，"
                                             "或在设置里调低「文字置信度阈值」。")
                return
        else:
            text = preset_text
            if ocr_result is None:
                ocr_result = ocr_pkg.OcrResult(text, [], "text", 0.0)

        # ---- 2. 翻译 ----
        try:
            result = tr_pkg.translate(text, src, dst, tcfg)
        except Exception as e:  # noqa: BLE001
            if self._alive(gen):
                self.failed.emit("translate", "%s" % (str(e) or type(e).__name__))
            return

        if self._alive(gen):
            self.finished.emit(ocr_result, result)
