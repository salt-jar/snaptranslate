# -*- coding: utf-8 -*-
"""Tesseract OCR 引擎（可选）。

需要系统里已安装 Tesseract（https://github.com/UB-Mannheim/tesseract/releases），
不需要 Python 侧的任何包，直接调用 ``tesseract.exe`` 并解析 TSV 输出。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from ..paths import cache_dir
from .base import OcrResult, TextBox, lines_to_text
from .preprocess import prepare_png

_CREATE_NO_WINDOW = 0x08000000

_LANG_ARGS = {
    "ch": "chi_sim+eng",
    "chinese_cht": "chi_tra+eng",
    "en": "eng",
    "japan": "jpn+eng",
    "korean": "kor+eng",
    "latin": "eng",
    "cyrillic": "rus+eng",
}

_SEARCH = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def find_tesseract() -> Optional[str]:
    hit = shutil.which("tesseract")
    if hit:
        return hit
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cand = Path(local) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
        if cand.exists():
            return str(cand)
        cand = Path(local) / "Tesseract-OCR" / "tesseract.exe"
        if cand.exists():
            return str(cand)
    for p in _SEARCH:
        if Path(p).exists():
            return p
    return None


class TesseractEngine:
    key = "tesseract"
    label = "Tesseract OCR"
    detail = "需要系统安装 Tesseract，适合已经装好它的用户"

    def __init__(self, cfg: dict):
        self._cfg = dict(cfg or {})
        self._exe = find_tesseract()

    @classmethod
    def available(cls) -> bool:
        return find_tesseract() is not None

    @classmethod
    def unavailable_reason(cls) -> str:
        return ("未找到 tesseract.exe。可安装 Tesseract-OCR 后重试，"
                "或在设置里改用 RapidOCR / Windows OCR。")

    def recognize(self, qimg) -> OcrResult:
        t0 = time.perf_counter()
        w, h = qimg.width(), qimg.height()
        if not self._exe:
            raise RuntimeError(self.unavailable_reason())

        png, scale = prepare_png(
            qimg,
            upscale=float(self._cfg.get("upscale", 2.0) or 1.0),
            threshold=int(self._cfg.get("upscale_threshold", 900) or 900),
            enhance=bool(self._cfg.get("enhance", True)),
        )
        if not png:
            return OcrResult("", [], self.key, 0.0, w, h)
        img_path = cache_dir() / "tesseract_input.png"
        img_path.write_bytes(png)

        lang = _LANG_ARGS.get(str(self._cfg.get("lang") or "ch"), "chi_sim+eng")
        proc = subprocess.run(
            [self._exe, str(img_path), "stdout", "-l", lang, "--psm", "6", "tsv"],
            capture_output=True, timeout=120, creationflags=_CREATE_NO_WINDOW,
        )
        out = (proc.stdout or b"").decode("utf-8", "replace")
        if not out.strip():
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
            raise RuntimeError("Tesseract 未返回结果：%s" % (err[:300] or "请检查语言包 " + lang))

        boxes: List[TextBox] = []
        lines: dict = {}
        header = True
        for row in out.splitlines():
            if header:
                header = False
                continue
            cols = row.split("\t")
            if len(cols) < 12:
                continue
            try:
                level = int(cols[0])
                if level != 5:                      # 5 = word
                    continue
                key = (cols[1], cols[2], cols[3], cols[4])
                x, y, bw, bh = int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9])
                conf = float(cols[10])
            except (ValueError, IndexError):
                continue
            text = cols[11].strip()
            if not text or conf < 0:
                continue
            lines.setdefault(key, []).append((x, y, bw, bh, text, conf))

        for key in sorted(lines, key=lambda k: (int(k[1]), int(k[2]), int(k[3]))):
            words = sorted(lines[key], key=lambda t: t[0])
            joined = ""
            for _x, _y, _w, _h, text, _c in words:
                if joined and not joined.endswith((" ", "-")) and text[:1].isalnum():
                    joined += " "
                joined += text
            if not joined.strip():
                continue
            x0 = min(wd[0] for wd in words)
            y0 = min(wd[1] for wd in words)
            x1 = max(wd[0] + wd[2] for wd in words)
            y1 = max(wd[1] + wd[3] for wd in words)
            boxes.append(TextBox(x0 / scale, y0 / scale, x1 / scale, y1 / scale, joined, 1.0))

        # Tesseract 的 TSV 顺序本身已是阅读顺序，直接拼行
        text = lines_to_text([[b] for b in boxes], keep_indent=False) if boxes else ""
        return OcrResult(text.strip(), boxes, self.key, time.perf_counter() - t0, w, h)
