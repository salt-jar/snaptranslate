# -*- coding: utf-8 -*-
"""生成程序图标 resources/icon.ico（多尺寸）与 icon.png。

纯 Pillow 绘制，不依赖任何设计文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "resources"

SIZE = 1024          # 超采样画布，最后再降采样，边缘更干净
RADIUS = 232         # 圆角半径
C1 = (76, 141, 255)      # #4c8dff
C2 = (124, 92, 255)      # #7c5cff


def gradient(size: int) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel((0, y), tuple(int(C1[i] + (C2[i] - C1[i]) * t) for i in range(3)))
    return grad.resize((size, size))


def find_font(size: int):
    for path in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
                 r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msjhbd.ttc"):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def build() -> Image.Image:
    base = gradient(SIZE).convert("RGBA")

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], RADIUS, fill=255)
    base.putalpha(mask)

    draw = ImageDraw.Draw(base)

    # 取景框四角
    inset = 150
    arm = 170
    width = 46
    white = (255, 255, 255, 235)
    corners = [
        (inset, inset, 1, 1), (SIZE - inset, inset, -1, 1),
        (inset, SIZE - inset, 1, -1), (SIZE - inset, SIZE - inset, -1, -1),
    ]
    for x, y, sx, sy in corners:
        draw.rounded_rectangle(
            [min(x, x + sx * arm), min(y, y + sy * width),
             max(x, x + sx * arm), max(y, y + sy * width)],
            width // 2, fill=white,
        )
        draw.rounded_rectangle(
            [min(x, x + sx * width), min(y, y + sy * arm),
             max(x, x + sx * width), max(y, y + sy * arm)],
            width // 2, fill=white,
        )

    # 中间的「译」
    font = find_font(int(SIZE * 0.44))
    text = "译"
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((SIZE - tw) / 2 - box[0], (SIZE - th) / 2 - box[1] - SIZE * 0.012),
              text, font=font, fill=(255, 255, 255, 255))
    return base


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = build()

    ico = OUT_DIR / "icon.ico"
    sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64),
             (128, 128), (256, 256)]
    img.save(ico, format="ICO", sizes=sizes)

    png = OUT_DIR / "icon.png"
    img.resize((256, 256), Image.LANCZOS).save(png)

    print("已生成：%s" % ico)
    print("已生成：%s" % png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
