# -*- coding: utf-8 -*-
"""翻译质量诊断：用几组针对性用例，把当前链路的具体失效模式暴露出来。

每组用例对应一类真实场景，并标注"这一组在检验什么"。
输出会直接显示：译文、耗时、是否保留行结构。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

from app.config import config  # noqa: E402
from app.translate import clear_cache, translate  # noqa: E402

CASES = [
    (
        "A. 短句（基线）",
        "检验最基本的翻译质量",
        "The quick brown fox jumps over the lazy dog.",
        "zh-CHS",
    ),
    (
        "B. 多行 UI 文本（中英混排）",
        "检验混排策略：中文行会不会被一起丢进去翻译",
        "截图翻译测试 ScreenshotTranslationTest\n"
        "This is a small font line for OCR accuracy.\n"
        "第二行：小字号中文识别，包含数字 12345 与符号 #@！。\n"
        "快捷键 Ctrl+Alt+Z 触发截图翻译。",
        "zh-CHS",
    ),
    (
        "C. 技术文本（术语与代码）",
        "检验术语与代码标识符是否被乱译",
        "The GPU inference backend uses ONNX Runtime with INT8 quantization.\n"
        "Set the timeout to 30s in config.json before starting the service.\n"
        "RapidOCR is based on PaddleOCR's PP-OCRv4 model.",
        "zh-CHS",
    ),
    (
        "D. 长段落（超过单次请求上限）",
        "检验长文本是否还能保留行结构（关键！）",
        "\n".join([
            "第一段：这个工具可以识别屏幕上的文字并翻译。",
            "第二段：识别部分完全离线，使用本地的 OCR 引擎。",
            "第三段：翻译部分支持在线引擎和离线语言包两种模式。",
            "第四段：如果选择离线模式，文本不会离开你的电脑。",
            "第五段：这段话故意写得比较长，用来超过单次请求的长度上限。",
        ] * 6),
        "en",
    ),
    (
        "E. 英文长段落",
        "检验英文侧的行结构与段落切分",
        "\n".join([
            "Screenshot translation tools recognise text on screen and translate it.",
            "The recognition stage runs entirely offline using a local OCR engine.",
            "The translation stage supports both online engines and offline packs.",
            "If you pick offline mode, your text never leaves your computer.",
            "This paragraph is intentionally long enough to exceed the per-request limit.",
        ] * 6),
        "zh-CHS",
    ),
    (
        "F. 口语/短促 UI 文案",
        "检验短文本与 auto 语种识别是否可靠",
        "Save changes?",
        "zh-CHS",
    ),
]

ENGINES = [("youdao_free", "在线·有道"), ("local", "本地离线")]


def count_lines(t: str) -> int:
    return len([x for x in (t or "").split("\n") if x.strip()])


def main() -> int:
    base = dict(config.section("translate"))
    print("=" * 78)
    print("  翻译质量诊断")
    print("=" * 78)
    print("  单次请求上限：max_chunk=%s 字符   文本超限后会被切段" % base.get("max_chunk"))

    for title, purpose, text, dst in CASES:
        print("\n" + "─" * 78)
        print("  %s" % title)
        print("  检验点：%s" % purpose)
        print("  源文 %d 字符 / %d 行" % (len(text), count_lines(text)))
        print("─" * 78)
        for line in text.split("\n")[:4]:
            print("    src | %s" % line[:66])
        if count_lines(text) > 4:
            print("    src | ...（共 %d 行）" % count_lines(text))

        for key, label in ENGINES:
            cfg = dict(base)
            cfg["engine"] = key
            clear_cache()
            try:
                t0 = time.perf_counter()
                res = translate(text, "auto", dst, cfg)
                dt = (time.perf_counter() - t0) * 1000
            except Exception as e:  # noqa: BLE001
                print("\n    [%s] 失败：%s" % (label, str(e)[:100]))
                continue
            out_lines = count_lines(res.text)
            flag = ""
            if count_lines(text) > 1:
                flag = "  <<< 行结构丢失！%d 行 → %d 行" % (count_lines(text), out_lines) \
                    if out_lines < count_lines(text) * 0.6 else "  （行结构保留）"
            print("\n    [%s] %.0fms  检测=%s%s" % (label, dt, res.detected or "?", flag))
            for line in res.text.split("\n")[:4]:
                print("      out | %s" % line[:66])
            if out_lines > 4:
                print("      out | ...（共 %d 行）" % out_lines)
    print("\n" + "=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
