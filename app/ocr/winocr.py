# -*- coding: utf-8 -*-
"""Windows 自带 OCR 引擎（零依赖兜底）。

Windows 10/11 内置了 OCR 语言包（``设置 → 时间和语言 → 语言`` 里可添加），
通过 Windows PowerShell 5.1 的 WinRT 桥接直接调用，不需要安装任何 Python 包。

识别质量不如 RapidOCR（容易把 l 认成 I、5 认成 S），但在没有第三方依赖时
仍可正常使用。中文语言包会把汉字用空格隔开，这里会做后处理还原。
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from ..paths import cache_dir
from .base import OcrResult, TextBox, lines_to_text, merge_into_lines
from .preprocess import prepare_png

_PS1 = Path(__file__).with_name("winocr.ps1")
_CREATE_NO_WINDOW = 0x08000000

# 内部语言代码 -> WinRT 语言标记
_LANG_TAG = {
    "ch": "zh-Hans-CN",
    "chinese_cht": "zh-Hant-TW",
    "en": "en-US",
    "japan": "ja-JP",
    "korean": "ko-KR",
    "latin": "en-US",
}

_CJK = r"\u2e80-\u9fff\u3000-\u303f\uff00-\uffef"
_RE_CJK_SPACE = re.compile(r"(?<=[%s])[ \t]+(?=[%s])" % (_CJK, _CJK))


def despace_cjk(text: str) -> str:
    """去掉 Windows OCR 在汉字之间插入的空格。"""
    return _RE_CJK_SPACE.sub("", text)


def _powershell() -> str:
    for name in ("powershell.exe", "pwsh.exe"):
        for base in (r"C:\Windows\System32\WindowsPowerShell\v1.0", None):
            cand = Path(base) / name if base else None
            if cand and cand.exists():
                return str(cand)
        return name
    return "powershell.exe"


class WinOcrEngine:
    key = "winocr"
    label = "Windows 自带 OCR"
    detail = "无需安装任何依赖，但精度一般；中文识别结果需去空格"

    def __init__(self, cfg: dict):
        self._cfg = dict(cfg or {})

    # ---------------------------------------------------------------- 可用性

    @classmethod
    def available(cls) -> bool:
        if not _PS1.exists():
            return False
        try:
            out = subprocess.run(
                [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                 "[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]"
                 " | Out-Null; if ([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages"
                 ".Count -gt 0) { 'OK' } else { 'NONE' }"],
                capture_output=True, text=True, timeout=25,
                creationflags=_CREATE_NO_WINDOW, encoding="utf-8", errors="replace",
            )
            return "OK" in (out.stdout or "")
        except Exception:
            return False

    @classmethod
    def unavailable_reason(cls) -> str:
        return ("未检测到 Windows OCR 语言包。可在「设置 → 时间和语言 → 语言和区域」"
                "中为中文添加“可选语言功能 → 光学字符识别”。")

    # ---------------------------------------------------------------- 识别

    def recognize(self, qimg) -> OcrResult:
        t0 = time.perf_counter()
        png, scale = prepare_png(
            qimg,
            upscale=float(self._cfg.get("upscale", 2.0) or 1.0),
            threshold=int(self._cfg.get("upscale_threshold", 900) or 900),
            enhance=bool(self._cfg.get("enhance", True)),
        )
        w, h = qimg.width(), qimg.height()
        if not png:
            return OcrResult("", [], self.key, 0.0, w, h)

        img_path = cache_dir() / "winocr_input.png"
        img_path.write_bytes(png)

        tag = _LANG_TAG.get(str(self._cfg.get("lang") or "ch"), "zh-Hans-CN")
        proc = subprocess.run(
            [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_PS1),
             "-Path", str(img_path), "-LangTag", tag],
            capture_output=True, timeout=60, creationflags=_CREATE_NO_WINDOW,
        )
        stdout = (proc.stdout or b"").decode("utf-8", "replace")
        stderr = (proc.stderr or b"").decode("utf-8", "replace")
        if proc.returncode != 0 and not stdout.strip():
            raise RuntimeError("Windows OCR 失败：%s" % (stderr.strip()[:300] or "未知错误"))

        boxes: List[TextBox] = []
        for raw_line in stdout.splitlines():
            parts = raw_line.split("\t")
            if len(parts) < 5:
                continue
            try:
                x, y, bw, bh = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
            except ValueError:
                continue
            text = despace_cjk("\t".join(parts[4:]).strip())
            if not text:
                continue
            if scale and scale > 1.0:
                x, y, bw, bh = x / scale, y / scale, bw / scale, bh / scale
            boxes.append(TextBox(x, y, x + bw, y + bh, text, 1.0))

        if self._cfg.get("merge_lines", True):
            lines = merge_into_lines(boxes, float(self._cfg.get("line_tolerance", 0.6)))
        else:
            lines = [[b] for b in sorted(boxes, key=lambda b: (b.cy, b.x0))]
        return OcrResult(lines_to_text(lines), boxes, self.key,
                         time.perf_counter() - t0, w, h)
