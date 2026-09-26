# -*- coding: utf-8 -*-
"""按字符系统做语种判定。

对截图翻译来说，"这段文字是中文还是西文"用字符区间统计就足够可靠，
而且**纯本地、零延迟** —— 比先发一次请求让引擎去检测快得多。

它还解决了「目标语言选自动」的一个体验问题：原来的做法是"先按中文译一次，
发现结果没变化再翻转成英文"，要发两次请求；现在直接本地定方向，一次搞定。
"""
from __future__ import annotations

from typing import Dict

#: 内部语言代码 -> 主要字符系统
_TARGET_SCRIPT = {
    "zh-CHS": "han", "zh-CHT": "han", "ja": "kana", "ko": "hangul",
    "ru": "cyrillic", "uk": "cyrillic", "bg": "cyrillic",
    "ar": "arabic", "he": "hebrew", "th": "thai", "hi": "devanagari",
    "el": "greek",
}

_CJK_LANGS = ("zh-CHS", "zh-CHT", "ja", "ko")


def script_counts(text: str) -> Dict[str, int]:
    """统计各字符系统出现的次数。"""
    c = {"han": 0, "kana": 0, "hangul": 0, "cyrillic": 0, "latin": 0,
         "arabic": 0, "thai": 0, "hebrew": 0, "greek": 0, "devanagari": 0}
    for ch in text or "":
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            c["han"] += 1
        elif 0x3040 <= o <= 0x30FF:
            c["kana"] += 1
        elif 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            c["hangul"] += 1
        elif 0x0400 <= o <= 0x04FF:
            c["cyrillic"] += 1
        elif 0x0600 <= o <= 0x06FF:
            c["arabic"] += 1
        elif 0x0E00 <= o <= 0x0E7F:
            c["thai"] += 1
        elif 0x0590 <= o <= 0x05FF:
            c["hebrew"] += 1
        elif 0x0370 <= o <= 0x03FF:
            c["greek"] += 1
        elif 0x0900 <= o <= 0x097F:
            c["devanagari"] += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            c["latin"] += 1
    return c


def script_of(text: str) -> str:
    """返回这段文字的主要字符系统名；判断不出来时返回 ``latin``。"""
    c = script_counts(text)
    total = sum(c.values())
    if total == 0:
        return "latin"
    # 假名/谚文优先级最高（否则日文会被汉字抢走）
    for key in ("kana", "hangul"):
        if c[key] > 0:
            return key
    # 其余按占比最高者胜出
    return max(c, key=lambda k: c[k])


def dominant(text: str) -> str:
    """返回主要语言（内部代码风格）。"""
    s = script_of(text)
    return {"han": "zh", "kana": "ja", "hangul": "ko", "cyrillic": "ru",
            "arabic": "ar", "thai": "th", "hebrew": "he", "greek": "el",
            "devanagari": "hi"}.get(s, "en")


def target_script(dst: str) -> str:
    """目标语言对应的字符系统。"""
    return _TARGET_SCRIPT.get(dst, "latin")


def cjk_ratio(text: str) -> float:
    """汉字在全部"字母类字符"中的占比。用于判断「几乎全中文」的场景。"""
    c = script_counts(text)
    letters = c["han"] + c["kana"] + c["hangul"] + c["latin"] + c["cyrillic"] + \
        c["arabic"] + c["thai"] + c["hebrew"] + c["greek"] + c["devanagari"]
    if letters == 0:
        return 0.0
    return c["han"] / letters


#: 判定"这行已经是目标语言"时，目标字符系统需要占到的比例。
#:
#: 中日韩目标放宽到 0.15，理由是**风险不对称**：
#: * 把该翻的行留着没翻 —— 用户看到一段没译的外文，内容还在；
#: * 把已经是中文的行送去翻 —— 中文部分会被引擎改掉甚至整段丢掉
#:   （实测 `截图翻译测试 ScreenshotTranslationTest` 送进离线引擎后，
#    中文部分直接没了，只剩 `ScreenshotTranslationTest`）。
#: 后者更糟，所以宁可保守。
#:
#: 这个值也覆盖了 `快捷键 Ctrl+Alt+Z 触发截图翻译。`（汉字占 0.53）
#: 和 `快捷键 Ctrl+Alt+Z 触发`（0.38）这类"中文夹快捷键"的行。
_KEEP_RATIO_CJK = 0.15
_KEEP_RATIO_OTHER = 0.5


def is_target_language(text: str, dst: str) -> bool:
    """这段文字是不是已经是目标语言了（用于「这行不用翻」的判断）。"""
    if not (text or "").strip():
        return True
    want = target_script(dst)
    c = script_counts(text)
    letters = sum(c.values())
    if letters == 0:
        return True          # 纯符号/数字，翻了也没意义
    if want == "latin":
        # 拉丁目标：只要出现汉字/假名/谚文，就认为这行还需要翻译
        if c["han"] or c["kana"] or c["hangul"]:
            return False
        return c["latin"] / letters >= _KEEP_RATIO_OTHER
    ratio = c.get(want, 0) / letters
    threshold = _KEEP_RATIO_CJK if want in ("han", "kana", "hangul") else _KEEP_RATIO_OTHER
    return ratio >= threshold


def is_cjk_lang(lang: str) -> bool:
    return lang in _CJK_LANGS
