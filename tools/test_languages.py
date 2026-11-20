# -*- coding: utf-8 -*-
"""语言覆盖与多语种翻译路径的回归测试。

覆盖三块：

1. 语言注册表：100+ 语种、代码唯一、每个语种都有显示名和各家映射；
2. 语种判定：拉丁目标不能被"字符系统相同"错误跳过，中日韩仍保留分行逻辑；
3. 翻译门面：用一个假引擎验证「英语→法语」不会被反向翻成中文，
   「法语原文 + 法语目标」会兜底译成英文。

用法::

    python tools/test_languages.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

import app.translate as tr  # noqa: E402
from app.langs import (  # noqa: E402
    LANGS,
    TARGETS,
    label,
    normalize_code,
    to_baidu,
    to_google,
    to_llm_name,
    to_mymemory,
    to_yandex,
)
from app.translate.base import Provider  # noqa: E402
from app.translate.langdetect import (  # noqa: E402
    dominant,
    is_target_language,
    script_of,
    target_script,
)

PASS = 0
FAIL = 0
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print("  [OK]  %s" % name)
    else:
        FAIL += 1
        FAILURES.append(name + (("（%s）" % detail) if detail else ""))
        print("  [!!]  %s%s" % (name, ("（%s）" % detail) if detail else ""))


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print("  " + title)
    print("=" * 72)


def test_registry() -> None:
    section("1. 语言注册表")
    codes = [code for code, _ in LANGS]
    check("语言数量 ≥ 100", len(LANGS) - 1 >= 100, "实际 %d" % (len(LANGS) - 1))
    check("代码唯一", len(codes) == len(set(codes)))
    check("每种语言都有中文名", all(name.strip() for _, name in LANGS))
    check("目标语言 = 自动 + 全部语言", len(TARGETS) == len(LANGS))
    check("目标语言包含自动", TARGETS[0][0] == "auto")

    bad = []
    for code in codes:
        if code == "auto":
            continue
        for fn in (label, to_google, to_mymemory, to_yandex, to_baidu, to_llm_name):
            try:
                if not str(fn(code)).strip():
                    bad.append((code, fn.__name__))
            except Exception as e:  # noqa: BLE001
                bad.append((code, fn.__name__, str(e)[:40]))
    check("所有语言都有显示名 / 各家代码映射", not bad, repr(bad[:5]))

    check("中文简体映射 Google", to_google("zh-CHS") == "zh-CN")
    check("中文繁体映射 Google", to_google("zh-CHT") == "zh-TW")
    check("希伯来语映射 Google 的 iw", to_google("he") == "iw")
    check("爪哇语映射 Google 的 jw", to_google("jv") == "jw")
    check("中文映射百度", to_baidu("zh-CHS") == "zh" and to_baidu("zh-CHT") == "cht")
    check("日语映射百度", to_baidu("ja") == "jp")
    check("Yandex 中文不区分简繁", to_yandex("zh-CHS") == to_yandex("zh-CHT") == "zh")
    check("LLM 中文目标名", to_llm_name("fr") == "法语")


def test_normalize() -> None:
    section("2. 语言代码归一化")
    cases = {
        "zh-CN": "zh-CHS",
        "zh_CN": "zh-CHS",
        "zh-TW": "zh-CHT",
        "zt": "zh-CHT",
        "iw": "he",
        "jw": "jv",
        "nb": "no",
        "pb": "pt",
        "jp": "ja",
        "kor": "ko",
        "fra": "fr",
        "deu": "de",
        "may": "ms",
        "fil": "tl",
        "nosuch": "nosuch",
    }
    for src, want in cases.items():
        check("%s → %s" % (src, want), normalize_code(src) == want,
              "得到 %r" % normalize_code(src))


def test_detection() -> None:
    section("3. 语种与目标文字系统")
    check("英语主要字符系统", script_of("Hello world") == "latin")
    check("中文主要字符系统", script_of("你好世界") == "han")
    check("日文假名优先", script_of("こんにちは世界") == "kana")
    check("韩文主要字符系统", script_of("안녕하세요") == "hangul")
    check("西里尔识别为 ru", dominant("Привет") == "ru")
    check("孟加拉文", target_script("bn") == "bengali")
    check("泰米尔文", target_script("ta") == "tamil")
    check("目标越南语按拉丁处理", target_script("vi") == "latin")

    # 拉丁目标不做"字符系统级跳过"：英语原文译法语时必须真的送去翻译
    check("英语原文 + 法语目标：不跳过", not is_target_language("Hello world", "fr"))
    check("法语原文 + 法语目标：不按字符系统跳过",
          not is_target_language("Bonjour tout le monde", "fr"))
    check("英语原文 + 英文目标：不按字符系统跳过",
          not is_target_language("Hello world", "en"))
    check("英文原文 + 中文目标：需翻译", not is_target_language("Hello world", "zh-CHS"))
    check("中文原文 + 中文目标：保留", is_target_language("你好世界", "zh-CHS"))
    check("日文假名 + 日文目标：保留", is_target_language("こんにちは", "ja"))
    check("韩文 + 韩文目标：保留", is_target_language("안녕하세요", "ko"))
    check("纯数字 / 符号：保留", is_target_language("12345 #@!", "zh-CHS"))
    check("西里尔目标同样不按字符跳过", not is_target_language("Привет", "ru"))

    # _plan_lines 在拉丁目标下应当整段翻译，不能把英文行当成"已经是法语"
    lines, need = tr._plan_lines("Hello world\nThis is a test.", "fr")
    check("拉丁目标不进入分行过滤", lines is None and need is None)

    lines2, need2 = tr._plan_lines(
        "截图翻译测试\nThis is a test.\n第二行中文。", "zh-CHS")
    check("中文目标仍保留分行过滤", lines2 is not None and need2 == [1],
          "need=%r" % need2)


def test_flip_rules() -> None:
    section("4. 反向翻译规则")
    check("目标中文 → 英文", tr._flip_target("zh-CHS") == "en")
    check("目标英文 → 中文", tr._flip_target("en") == "zh-CHS")
    check("目标法语 → 英文（不是中文）", tr._flip_target("fr") == "en")
    check("目标日语 → 英文", tr._flip_target("ja") == "en")
    check("目标繁体中文 → 英文", tr._flip_target("zh-CHT") == "en")
    check("繁体中文优先走支持 zh-TW 的通道",
          tr.auto_order("zh-CHT")[:2] == ["mymemory", "google_free"],
          "顺序=%r" % (tr.auto_order("zh-CHT")[:3],))

    from app.translate.base import TranslateResult

    check("检测到法语 + 目标法语 → 反向",
          tr._needs_flip("Bonjour", TranslateResult("Bonjour", "x", 0.1, "fr"),
                         "auto", "fr"))
    check("检测到英语 + 目标法语 → 不反向",
          not tr._needs_flip("Hello", TranslateResult("Bonjour", "x", 0.1, "en"),
                             "auto", "fr"))
    check("原文未变化 + 目标法语 → 反向",
          tr._needs_flip("Bonjour", TranslateResult("Bonjour", "x", 0.1, ""),
                         "auto", "fr"))
    check("检测到中文简繁 → 归一后可判断",
          tr._needs_flip("你好", TranslateResult("你好", "x", 0.1, "zh-CN"),
                         "auto", "zh-CHS"))


class DummyProvider(Provider):
    key = "dummy"
    label = "测试引擎"
    max_chunk = 10000
    last_calls = []

    @classmethod
    def available(cls, cfg):
        return True, ""

    def translate_chunk(self, text, src, dst):
        DummyProvider.last_calls.append((src, dst, text))
        french = text.startswith("Bonjour")
        if dst == "fr":
            if french:
                return text, "fr"          # 模拟"已经是目标语言"
            return "FR:" + text, "en"
        if dst == "en":
            if french:
                return "EN:" + text, "fr"
            return text, "en"              # 英文原文原样返回
        if dst == "zh-CHS":
            return "ZH:" + text, "en"
        return text, ""


def test_translate_paths() -> None:
    section("5. 多语种翻译路径（假引擎，不联网）")
    tr._BY_KEY["dummy"] = DummyProvider
    try:
        cfg = {"engine": "dummy", "fallback": False, "glossary": []}

        DummyProvider.last_calls = []
        res = tr.translate("Hello world", "auto", "fr", cfg, use_cache=False)
        check("英语 → 法语：确实送到法语目标",
              res.text == "FR:Hello world" and DummyProvider.last_calls
              and DummyProvider.last_calls[0][1] == "fr",
              "calls=%r text=%r" % (DummyProvider.last_calls, res.text))

        DummyProvider.last_calls = []
        res = tr.translate("Bonjour tout le monde", "auto", "fr", cfg,
                           use_cache=False)
        check("法语原文 + 法语目标：兜底翻成英文，而不是中文",
              res.text == "EN:Bonjour tout le monde"
              and [c[1] for c in DummyProvider.last_calls] == ["fr", "en"],
              "calls=%r text=%r" % (DummyProvider.last_calls, res.text))
        check("反向提示里写的是英语", "英语" in res.note, "note=%r" % res.note)

        DummyProvider.last_calls = []
        res = tr.translate("Hello world", "auto", "en", cfg, use_cache=False)
        check("英文原文 + 英文目标：反向翻成中文",
              res.text == "ZH:Hello world"
              and [c[1] for c in DummyProvider.last_calls] == ["en", "zh-CHS"],
              "calls=%r text=%r" % (DummyProvider.last_calls, res.text))
    finally:
        tr._BY_KEY.pop("dummy", None)


def main() -> int:
    print("截译 · 多语种回归测试")
    test_registry()
    test_normalize()
    test_detection()
    test_flip_rules()
    test_translate_paths()

    print("\n" + "=" * 72)
    print("  通过 %d  失败 %d" % (PASS, FAIL))
    for f in FAILURES:
        print("    · " + f)
    print("=" * 72)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
