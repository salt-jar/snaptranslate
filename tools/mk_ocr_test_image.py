# -*- coding: utf-8 -*-
"""生成 OCR 测试图片。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "ocr_test.png"


def font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    W, H = 900, 380
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 24), "截图翻译测试 Screenshot Translation Test", font=font(34), fill="black")
    d.text((30, 90), "This is a small font line for OCR accuracy.", font=font(18), fill="#222222")
    d.text((30, 130), "第二行：小字号中文识别，包含数字 12345 与符号 #@!。", font=font(18), fill="#222222")
    d.text((30, 180), "Mixed 中英文 mixed content with 标点，句号结束。", font=font(22), fill="#0a3d62")
    d.text((30, 230), "Paragraph wrapping test: the quick brown fox jumps over the lazy dog.", font=font(16), fill="#333333")
    d.text((30, 256), "第二个段落换行测试：敏捷的棕色狐狸跳过了懒狗。", font=font(16), fill="#333333")
    d.text((30, 310), "Colored text 彩色文字 should still be readable.", font=font(20), fill="#b71540")

    # 深色主题样本
    dark = Image.new("RGB", (900, 200), "#1b1d22")
    dd = ImageDraw.Draw(dark)
    dd.text((30, 30), "Dark theme 深色主题 OCR 测试", font=font(30), fill="#e8eaed")
    dd.text((30, 90), "Light text on dark background, small size 16px.", font=font(16), fill="#c9ced8")
    dd.text((30, 130), "快捷键 Ctrl+Alt+Z 触发截图翻译。", font=font(18), fill="#9aa0ab")

    canvas = Image.new("RGB", (W, H + 200 + 20), "gray")
    canvas.paste(img, (0, 0))
    canvas.paste(dark, (0, H + 20))
    canvas.save(OUT)
    print(OUT)


if __name__ == "__main__":
    sys.exit(main())
