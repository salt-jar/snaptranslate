# -*- coding: utf-8 -*-
"""翻译链路回归测试。

这组用例对应的是实际踩过的坑，每条都有明确的断言，防止以后又改回去：

* **长文本丢行结构** —— `chunk_text` 里的 `\\s*` 会吃掉换行，30 行变 1 行；
* **中英混排被整篇翻转** —— 目标选中文，输出却是英文；
* **代码/术语被改写** —— `config.json` → `config。json`、`PP-OCRv4` → `pp - ocr4`；
* **「自动」目标跑偏** —— 原来要发两次请求，还会在混排时判错方向。

用法::

    python tools/test_translation.py            # 全部（含联网用例）
    python tools/test_translation.py --no-net   # 只跑本地用例（断网也能跑）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

PASS, FAIL, SKIP = "  [OK]  ", "  [!!]  ", "  [--]  "

_results = {"pass": 0, "fail": 0, "skip": 0}
_failures = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        _results["pass"] += 1
        print("%s%s" % (PASS, name))
    else:
        _results["fail"] += 1
        _failures.append(name)
        print("%s%s" % (FAIL, name))
        if detail:
            for line in detail.splitlines()[:8]:
                print("        " + line)


def section(title: str) -> None:
    print("\n" + "=" * 74)
    print("  " + title)
    print("=" * 74)


# --------------------------------------------------------------------- 本地用例


def test_chunk_text() -> None:
    section("1. 分段：必须保住换行（旧实现会吃掉）")
    from app.translate.base import chunk_text

    short = "第一行。\n第二行。\n第三行。"
    got = chunk_text(short, 1400)
    check("短文本原样返回", got == [short], "得到 %r" % got)

    long_text = "这是第 %d 行内容，足够长以触发切段逻辑。\n"
    lines = [long_text % i for i in range(80)]
    text = "".join(lines).rstrip("\n")
    chunks = chunk_text(text, 400)
    check("长文本确实被切成了多段（%d 段）" % len(chunks), len(chunks) > 1,
          "没切段说明用例没触发真正的问题")
    check("每段都不超上限", all(len(c) <= 400 for c in chunks),
          "超限段长度：%s" % [len(c) for c in chunks if len(c) > 400])

    rebuilt = "\n".join(chunks)
    check("拼回后与原文逐行一致（%d 行）" % len(text.split("\n")),
          rebuilt == text,
          "行数 原文=%d 拼回=%d" % (len(text.split("\n")), len(rebuilt.split("\n"))))


def test_langdetect() -> None:
    section("2. 语种判定：混排行该不该翻")
    from app.translate.langdetect import cjk_ratio, dominant, is_target_language, script_of

    check("纯英文识别为 en", dominant("Hello world") == "en")
    check("纯中文识别为 zh", dominant("你好世界") == "zh")
    check("日文优先于汉字", script_of("こんにちは世界") == "kana")
    check("韩文识别为 hangul", script_of("안녕하세요") == "hangul")
    check("西里尔识别为 ru", dominant("Привет") == "ru")

    # 目标是中文时，这些行应当**原样保留**
    keep = [
        "你好世界",
        "第二行：小字号中文识别，包含数字 12345 与符号 #@！。",
        "快捷键 Ctrl+Alt+Z 触发截图翻译。",     # 汉字占 0.53
        "快捷键 Ctrl+Alt+Z 触发",              # 汉字占 0.38
        # 汉字只占 0.19，但**依然要保留**：送进引擎后中文部分会被吃掉。
        # 实测离线引擎把这一行译成了 `ScreenshotTranslationTest`，
        # 「截图翻译测试」直接消失。风险不对称，所以宁可保守。
        "截图翻译测试 ScreenshotTranslationTest",
        "12345",
        "#@!",
    ]
    translate_it = [
        "This is a small font line for OCR accuracy.",
        "config.json",
        "Hello 世 world",                      # 汉字仅占 0.08，确实以外文为主
    ]
    for t in keep:
        check("保留（已是中文）：%s" % t[:34],
              is_target_language(t, "zh-CHS"),
              "cjk_ratio=%.2f" % cjk_ratio(t))
    for t in translate_it:
        check("需翻译：%s" % t[:34],
              not is_target_language(t, "zh-CHS"),
              "cjk_ratio=%.2f" % cjk_ratio(t))

    check("目标为英文时，含汉字的行一律需翻译",
          not is_target_language("快捷键 Ctrl+Alt+Z 触发", "en"))


def test_auto_target() -> None:
    section("3. 「自动」目标：本地定方向，不再发两次请求")
    from app.translate import _auto_target

    check("纯英文 → 中文", _auto_target("Hello world, this is a test.") == "zh-CHS")
    check("纯中文 → 英文", _auto_target("你好世界，这是一个测试。") == "en")
    check("混排（中文占比低）→ 中文",
          _auto_target("截图翻译测试 ScreenshotTranslationTest") == "zh-CHS")


def test_plan_lines() -> None:
    section("4. 混排分行：只翻译外文行")
    from app.translate import _plan_lines

    mixed = ("截图翻译测试 ScreenshotTranslationTest\n"
             "This is a small font line for OCR accuracy.\n"
             "第二行：小字号中文识别，包含数字 12345 与符号 #@！。\n"
             "快捷键 Ctrl+Alt+Z 触发截图翻译。")
    lines, need = _plan_lines(mixed, "zh-CHS")
    check("混排时进入分行模式", lines is not None and need is not None)
    if need is not None:
        picked = [lines[i][:34] for i in need]
        # 4 行里只有第 2 行是纯英文，其余都含足够多的中文（含第 1 行那种半中文行）
        check("只挑出纯外文的那 1 行", len(need) == 1, "挑出：%s" % picked)
        check("中文行没被挑走",
              all("第二行" not in lines[i] for i in need) and
              all("快捷键" not in lines[i] for i in need) and
              all("截图翻译测试" not in lines[i] for i in need),
              "挑出：%s" % picked)

    all_en = "First line.\nSecond line.\nThird line."
    check("全外文时不进分行模式（走整段翻译，保持上下文）",
          _plan_lines(all_en, "zh-CHS") == (None, None))

    all_zh = "第一行。\n第二行。"
    check("全中文时不进分行模式", _plan_lines(all_zh, "zh-CHS") == (None, None))


def test_glossary() -> None:
    section("5. 术语与代码保护")
    from app.translate.glossary import Glossary

    # 实测被引擎改写过的几个
    for text, must_keep in [
        ("Set the timeout in config.json before starting.", "config.json"),
        ("RapidOCR is based on PaddleOCR PP-OCRv4.", "PP-OCRv4"),
        ("The GPU backend uses ONNX Runtime.", "ONNX"),
        ("See https://github.com/salt-jar/snaptranslate", "https://github.com/salt-jar/snaptranslate"),
        ("Press Ctrl+Alt+Z to capture.", "Ctrl+Alt+Z"),
        ("Upgrade to v1.1.0 later.", "v1.1.0"),
    ]:
        masked, slots = Glossary(None).protect(text)
        ok = must_keep not in masked and any(v == must_keep for v in slots.values())
        check("保护 %s" % must_keep, ok, "掩码后=%r 槽位=%s" % (masked, slots))

    # 普通句子不该被过度保护（保护过头会让这些句子得不到翻译）
    for plain in ["The quick brown fox jumps over the lazy dog.",
                  "This is a well-known up-to-date solution.",
                  "She said hello and walked away.",
                  "The service starts in 30 seconds."]:
        masked, slots = Glossary(None).protect(plain)
        check("不过度保护：%s" % plain[:34], masked == plain,
              "掩码后=%r 槽位=%s" % (masked, slots))

    # ---- 还原的容错：引擎会各种改写占位符 ----
    text = "Set the timeout in config.json."
    masked, slots = Glossary(None).protect(text)
    key = [k for k, v in slots.items() if v == "config.json"][0]
    idx = key.strip("{}")
    cases = [
        ("正常形态 {%s}" % idx, "{%s}" % idx),
        ("括号里插空格 { %s }" % idx, "{ %s }" % idx),
        ("有道加粗变形 [b[%s]]" % idx, "[b[%s]]" % idx),
        ("历史格式 [[%s]]" % idx, "[[%s]]" % idx),
        ("被截断 [[%s]" % idx, "[[%s]" % idx),
    ]
    for label, form in cases:
        restored, lost = Glossary.restore("在 %s 中设置超时。" % form, slots)
        check("还原「%s」" % label, "config.json" in restored and not lost,
              "得到 %r 丢失=%s" % (restored, lost))

    # ---- 不能误伤译文里本来就有的括号数字 ----
    restored, _ = Glossary.restore("第一行（1）和第二行[2]都正常。", slots)
    check("不误伤译文里原有的括号数字",
          "（1）" in restored and "[2]" in restored, "得到 %r" % restored)

    # ---- 残留碎片必须清掉，不能泄漏到译文里 ----
    restored, lost = Glossary.restore("这是 [[9] 残骸和 [b[ 碎片。", slots)
    check("清掉被拆碎的占位符残骸",
          "[[" not in restored and "[b[" not in restored, "得到 %r" % restored)

    # ---- 用户术语：还原成指定译法 ----
    g = Glossary(["config.json=配置文件"])
    masked, slots = g.protect(text)
    check("用户术语被遮住", "config.json" not in masked, "掩码后=%r" % masked)
    restored, _ = Glossary.restore(masked, slots)
    check("用户术语还原成指定译法", "配置文件" in restored, "得到 %r" % restored)

    # ---- 源文本自带的 {0} 不能和占位符撞车 ----
    src = 'Use the format string "{0}" in config.json.'
    masked, slots = Glossary(None).protect(src)
    restored, lost = Glossary.restore(masked, slots)
    check("源文本自带的 {0} 不与占位符冲突",
          '"{0}"' in restored and "config.json" in restored,
          "掩码=%r 还原=%r" % (masked, restored))

    # 术语表解析
    check("解析 源=译", Glossary.parse_terms(["a=b", "c=d"]) == {"a": "b", "c": "d"})
    check("解析 源=>译", Glossary.parse_terms(["a=>b"]) == {"a": "b"})
    check("解析 单列词=保持原样", Glossary.parse_terms(["GPU"]) == {"GPU": "GPU"})
    check("忽略注释", Glossary.parse_terms(["# 说明", "a=b"]) == {"a": "b"})

    # 不该误伤正常句子
    plain = "The quick brown fox jumps over the lazy dog."
    masked, slots = Glossary(None).protect(plain)
    check("普通句子不被过度保护", masked == plain, "掩码后=%r 槽位=%s" % (masked, slots))


def test_regroup() -> None:
    section("6. 译文装回原文本")
    from app.translate import _regroup
    from app.translate.base import TranslateResult

    lines = ["第一行", "Second line", "第三行"]
    need = [1]
    r = TranslateResult("第二行", "x", 0.1)
    out = _regroup(r, lines, need)
    check("译文装回对应行", out.text == "第一行\n第二行\n第三行", "得到 %r" % out.text)

    r2 = TranslateResult("行数不对的译文\n多了一行", "x", 0.1)
    out2 = _regroup(r2, lines, need)
    check("行数对不上时保持整体译文（宁可丢结构也不要错位）",
          out2.text == "行数不对的译文\n多了一行", "得到 %r" % out2.text)


# --------------------------------------------------------------------- 联网用例


def test_online(cfg: dict) -> None:
    section("7. 端到端（联网）")
    from app.translate import clear_cache, translate

    def run(text, dst, engine="youdao_free"):
        c = dict(cfg)
        c["engine"] = engine
        clear_cache()
        return translate(text, "auto", dst, c)

    # 7.1 长文本行结构
    src_lines = [
        "Screenshot translation tools recognise text on screen and translate it.",
        "The recognition stage runs entirely offline using a local OCR engine.",
        "The translation stage supports both online engines and offline packs.",
        "If you pick offline mode, your text never leaves your computer.",
        "This paragraph is intentionally long enough to exceed the per-request limit.",
    ] * 6
    src = "\n".join(src_lines)
    try:
        res = run(src, "zh-CHS")
        got = len([x for x in res.text.split("\n") if x.strip()])
        check("长文本（%d 字符）行结构不丢失：%d 行 → %d 行"
              % (len(src), len(src_lines), got),
              got >= len(src_lines) * 0.9,
              "输出：%s" % res.text[:200])
    except Exception as e:  # noqa: BLE001
        _results["skip"] += 1
        print("%s长文本用例跳过（%s）" % (SKIP, str(e)[:60]))

    # 7.2 混排只翻外文行
    mixed = ("截图翻译测试 ScreenshotTranslationTest\n"
             "This is a small font line for OCR accuracy.\n"
             "第二行：小字号中文识别，包含数字 12345。")
    try:
        res = run(mixed, "zh-CHS")
        lines = res.text.split("\n")
        check("混排输出仍是中文（不会被整篇翻成英文）",
              any("\u4e00" <= ch <= "\u9fff" for ch in res.text),
              "输出：%r" % res.text)
        check("混排输出的行数没有塌陷（≥3 行）", len(lines) >= 3,
              "输出：%r" % res.text)
        if len(lines) >= 3:
            check("中文行原样保留（未被翻译）",
                  "第二行" in lines[2], "第 3 行：%r" % lines[2])
    except Exception as e:  # noqa: BLE001
        _results["skip"] += 1
        print("%s混排用例跳过（%s）" % (SKIP, str(e)[:60]))

    # 7.3 术语保护端到端
    tech = "Set the timeout in config.json, then run PP-OCRv4 with ONNX Runtime."
    try:
        res = run(tech, "zh-CHS")
        for token in ("config.json", "PP-OCRv4", "ONNX"):
            check("译文里 %s 未被改写" % token, token in res.text,
                  "输出：%r" % res.text)
    except Exception as e:  # noqa: BLE001
        _results["skip"] += 1
        print("%s术语用例跳过（%s）" % (SKIP, str(e)[:60]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-net", action="store_true", help="只跑本地用例")
    args = ap.parse_args()

    print("截译 · 翻译链路回归测试")

    test_chunk_text()
    test_langdetect()
    test_auto_target()
    test_plan_lines()
    test_glossary()
    test_regroup()

    if not args.no_net:
        from app.config import config

        test_online(dict(config.section("translate")))
    else:
        print("\n（已跳过联网用例）")

    print("\n" + "=" * 74)
    print("  通过 %d  失败 %d  跳过 %d"
          % (_results["pass"], _results["fail"], _results["skip"]))
    if _failures:
        print("  失败项：")
        for f in _failures:
            print("    · " + f)
    print("=" * 74)
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
