# -*- coding: utf-8 -*-
"""OCR 公共数据结构与后处理。"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

# CJK 与拉丁字母/数字的交界处补空格。PP-OCR 的中文模型经常吞掉空格
# （"测试ScreenshotTranslationTest"），补上后译文质量和可读性都明显变好。
# 只处理汉字/假名，不动全角标点，避免出现"你好 ，世界"这种错误。
_RE_CJK = r"\u2e80-\u9fff\u3040-\u30ff\uac00-\ud7af"
_RE_BOUNDARY = re.compile(
    r"(?<=[%s])(?=[0-9A-Za-z])|(?<=[0-9A-Za-z])(?=[%s])" % (_RE_CJK, _RE_CJK)
)


def normalize_spacing(text: str) -> str:
    """在汉字与西文之间补一个空格。"""
    return _RE_BOUNDARY.sub(" ", text)


@dataclass
class TextBox:
    """一个文本框。``x0,y0,x1,y1`` 为图像像素坐标。"""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    score: float = 1.0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def width(self) -> float:
        return abs(self.x1 - self.x0)

    @property
    def height(self) -> float:
        return abs(self.y1 - self.y0)

    @classmethod
    def from_polygon(cls, poly: Sequence[Sequence[float]], text: str, score: float = 1.0):
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        return cls(min(xs), min(ys), max(xs), max(ys), text, score)


@dataclass
class OcrResult:
    text: str
    boxes: List[TextBox] = field(default_factory=list)
    engine: str = ""
    elapsed: float = 0.0
    width: int = 0
    height: int = 0

    @property
    def empty(self) -> bool:
        return not self.text.strip()

    @property
    def box_count(self) -> int:
        return len(self.boxes)


# --------------------------------------------------------------------- 行归并


def _needs_space(left: str, right: str) -> bool:
    """西文之间补空格，CJK 之间不补。"""
    if not left or not right:
        return False
    a, b = left[-1], right[0]
    if a.isspace() or b.isspace():
        return False
    if b in ",.;:!?)]}%":
        return False
    if a in "([{":
        return False
    cjk = lambda ch: "\u2e80" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff" or "\uff00" <= ch <= "\uffef"
    return not (cjk(a) or cjk(b))


def merge_into_lines(boxes: Iterable[TextBox], tolerance: float = 0.6) -> List[List[TextBox]]:
    """把零散文本框按纵向重叠归并成"行"，并保持从左到右的阅读顺序。"""
    items = sorted(boxes, key=lambda b: (b.cy, b.x0))
    lines: List[dict] = []
    for box in items:
        placed = False
        for line in lines:
            ref: TextBox = line["ref"]
            ref_h = min(ref.height, box.height) or max(ref.height, box.height) or 1.0
            if abs(box.cy - ref.cy) <= tolerance * ref_h:
                line["items"].append(box)
                # 用加权中心修正参考行位置，避免逐行累积漂移
                line["ref"] = TextBox(
                    min(ref.x0, box.x0), min(ref.y0, box.y0),
                    max(ref.x1, box.x1), max(ref.y1, box.y1), "", 1.0,
                )
                placed = True
                break
        if not placed:
            lines.append({"ref": box, "items": [box]})

    lines.sort(key=lambda l: l["ref"].cy)
    out: List[List[TextBox]] = []
    for line in lines:
        line["items"].sort(key=lambda b: b.x0)
        out.append(line["items"])
    return out


def lines_to_text(lines: Sequence[Sequence[TextBox]], keep_indent: bool = True) -> str:
    """按行拼接文本；同一行内根据字符类型决定是否补空格。"""
    min_x = min((b.x0 for line in lines for b in line), default=0.0)
    rows: List[str] = []
    for line in lines:
        parts: List[str] = []
        for box in line:
            txt = box.text.strip()
            if not txt:
                continue
            if parts and _needs_space(parts[-1], txt):
                parts.append(" ")
            parts.append(txt)
        row = "".join(parts)
        if keep_indent and row and line:
            indent = line[0].x0 - min_x
            if indent > 12:
                row = " " * int(min(indent / 8.0, 12)) + row
        rows.append(normalize_spacing(row).rstrip())
    return "\n".join(rows).strip()


def raw_text(boxes: Sequence[TextBox]) -> str:
    return "\n".join(b.text for b in boxes if b.text.strip()).strip()


def estimate_angle(boxes: Sequence[TextBox]) -> float:
    """粗略估计文本倾斜角度（度），用于提示用户框选是否歪了。"""
    if len(boxes) < 4:
        return 0.0
    angles = []
    for b in boxes:
        if b.width > 12 and b.height > 2:
            angles.append(math.degrees(math.atan2(0, b.width)))
    return 0.0 if not angles else sum(angles) / len(angles)


def filter_boxes(boxes: Sequence[TextBox], min_score: float,
                 min_size: int = 2) -> List[TextBox]:
    return [
        b for b in boxes
        if b.score >= min_score and b.width >= min_size and b.height >= min_size
        and b.text.strip()
    ]
