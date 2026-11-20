# -*- coding: utf-8 -*-
"""按字符系统做语种判定。

对截图翻译来说，"这段文字是中文还是西文"用字符区间统计就足够可靠，
而且**纯本地、零延迟** —— 比先发一次请求让引擎去检测快得多。

它还解决了「目标语言选自动」的一个体验问题：原来的做法是"先按中文译一次，
发现结果没变化再翻转成英文"，要发两次请求；现在直接本地定方向，一次搞定。
"""
from __future__ import annotations

from typing import Dict

from ..langs import normalize_code

#: 内部语言代码 -> 主要字符系统。未列出的语言默认按拉丁字母处理。
_TARGET_SCRIPT = {
    "zh-CHS": "han", "zh-CHT": "han", "ja": "kana", "ko": "hangul",
    "ru": "cyrillic", "uk": "cyrillic", "bg": "cyrillic", "sr": "cyrillic",
    "mk": "cyrillic", "be": "cyrillic", "kk": "cyrillic", "ky": "cyrillic",
    "tg": "cyrillic", "mn": "cyrillic",
    "ar": "arabic", "fa": "arabic", "ur": "arabic", "ps": "arabic",
    "ku": "arabic", "sd": "arabic",
    "he": "hebrew", "yi": "hebrew",
    "el": "greek",
    "hi": "devanagari", "mr": "devanagari", "ne": "devanagari",
    "bn": "bengali", "as": "bengali",
    "pa": "gurmukhi", "gu": "gujarati", "ta": "tamil", "te": "telugu",
    "kn": "kannada", "ml": "malayalam", "si": "sinhala",
    "th": "thai", "lo": "lao", "km": "khmer", "my": "myanmar",
    "ka": "georgian", "hy": "armenian", "am": "ethiopic",
}

_CJK_LANGS = ("zh-CHS", "zh-CHT", "ja", "ko")

#: 需要按字符占比决定"这行是不是目标语言"的字符系统。
#: 只有中日韩这样做：拉丁/西里尔/阿拉伯等文字系统内部还包含很多语言，
#: 按字符系统判断会把「法语当成英语」「波斯语当成阿拉伯语」而错误跳过整行。
_FILTER_SCRIPTS = ("han", "kana", "hangul")


def script_counts(text: str) -> Dict[str, int]:
    """统计各字符系统出现的次数。"""
    c: Dict[str, int] = {
        "han": 0, "kana": 0, "hangul": 0, "cyrillic": 0, "latin": 0,
        "arabic": 0, "thai": 0, "hebrew": 0, "greek": 0, "devanagari": 0,
        "bengali": 0, "gurmukhi": 0, "gujarati": 0, "tamil": 0, "telugu": 0,
        "kannada": 0, "malayalam": 0, "sinhala": 0, "lao": 0, "myanmar": 0,
        "khmer": 0, "georgian": 0, "armenian": 0, "ethiopic": 0,
    }
    for ch in text or "":
        o = ord(ch)
        if (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
                or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x2A6DF):
            c["han"] += 1
        elif 0x3040 <= o <= 0x30FF or 0x31F0 <= o <= 0x31FF or 0xFF66 <= o <= 0xFF9D:
            c["kana"] += 1
        elif (0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF
              or 0x3130 <= o <= 0x318F):
            c["hangul"] += 1
        elif 0x0400 <= o <= 0x052F:
            c["cyrillic"] += 1
        elif (0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F
              or 0x08A0 <= o <= 0x08FF or 0xFB50 <= o <= 0xFDFF
              or 0xFE70 <= o <= 0xFEFF):
            c["arabic"] += 1
        elif 0x0530 <= o <= 0x058F:
            c["armenian"] += 1
        elif 0x0590 <= o <= 0x05FF:
            c["hebrew"] += 1
        elif 0x0370 <= o <= 0x03FF or 0x1F00 <= o <= 0x1FFF:
            c["greek"] += 1
        elif 0x0900 <= o <= 0x097F:
            c["devanagari"] += 1
        elif 0x0980 <= o <= 0x09FF:
            c["bengali"] += 1
        elif 0x0A00 <= o <= 0x0A7F:
            c["gurmukhi"] += 1
        elif 0x0A80 <= o <= 0x0AFF:
            c["gujarati"] += 1
        elif 0x0B80 <= o <= 0x0BFF:
            c["tamil"] += 1
        elif 0x0C00 <= o <= 0x0C7F:
            c["telugu"] += 1
        elif 0x0C80 <= o <= 0x0CFF:
            c["kannada"] += 1
        elif 0x0D00 <= o <= 0x0D7F:
            c["malayalam"] += 1
        elif 0x0D80 <= o <= 0x0DFF:
            c["sinhala"] += 1
        elif 0x0E00 <= o <= 0x0E7F:
            c["thai"] += 1
        elif 0x0E80 <= o <= 0x0EFF:
            c["lao"] += 1
        elif 0x1000 <= o <= 0x109F:
            c["myanmar"] += 1
        elif 0x10A0 <= o <= 0x10FF:
            c["georgian"] += 1
        elif 0x1200 <= o <= 0x137F:
            c["ethiopic"] += 1
        elif 0x1780 <= o <= 0x17FF:
            c["khmer"] += 1
        elif (0x0041 <= o <= 0x005A or 0x0061 <= o <= 0x007A
              or 0x00C0 <= o <= 0x024F or 0x1E00 <= o <= 0x1EFF
              or 0x2C60 <= o <= 0x2C7F or 0xA720 <= o <= 0xA7FF
              or 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A):
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
    """返回主要语言（内部代码风格；本地离线翻译会再转成 Argos 代码）。"""
    s = script_of(text)
    return {
        "han": "zh", "kana": "ja", "hangul": "ko", "cyrillic": "ru",
        "arabic": "ar", "thai": "th", "hebrew": "he", "greek": "el",
        "devanagari": "hi", "bengali": "bn", "gurmukhi": "pa",
        "gujarati": "gu", "tamil": "ta", "telugu": "te", "kannada": "kn",
        "malayalam": "ml", "sinhala": "si", "lao": "lo", "myanmar": "my",
        "khmer": "km", "georgian": "ka", "armenian": "hy", "ethiopic": "am",
    }.get(s, "en")


def target_script(dst: str) -> str:
    """目标语言对应的字符系统。"""
    return _TARGET_SCRIPT.get(normalize_code(dst), "latin")


def cjk_ratio(text: str) -> float:
    """汉字在全部"字母类字符"中的占比。用于判断「几乎全中文」的场景。"""
    c = script_counts(text)
    letters = sum(c.values())
    if letters == 0:
        return 0.0
    return c["han"] / letters


#: 判定"这行已经是目标语言"时，目标字符系统需要占到的比例。
#:
#: 中日韩目标放宽到 0.15，理由是**风险不对称**：
#: * 把该翻的行留着没翻 —— 用户看到一段没译的外文，内容还在；
#: * 把已经是中文的行送去翻 —— 中文部分会被引擎改掉甚至整段丢掉
#:   （实测 `截图翻译测试 ScreenshotTranslationTest` 送进离线引擎后，
#:    中文部分直接没了，只剩 `ScreenshotTranslationTest`）。
#:
#: 后者更糟，所以宁可保守。
#:
#: 这个值也覆盖了 `快捷键 Ctrl+Alt+Z 触发截图翻译。`（汉字占 0.53）
#: 和 `快捷键 Ctrl+Alt+Z 触发`（汉字占 0.38）这类"中文夹快捷键"的行。
_KEEP_RATIO_CJK = 0.15


def is_target_language(text: str, dst: str) -> bool:
    """这段文字是不是已经是目标语言了（用于「这行不用翻」的判断）。

    只有中日韩目标按字符占比判断。拉丁/西里尔/阿拉伯等文字系统内部有很多
    语言（英语和法语都是拉丁字母），按字符系统判断会把整行错误跳过，
    所以这些目标一律返回 ``False``，交给翻译引擎自己判断。
    """
    if not (text or "").strip():
        return True
    want = target_script(dst)
    c = script_counts(text)
    letters = sum(c.values())
    if letters == 0:
        return True          # 纯符号/数字，翻了也没意义
    if want not in _FILTER_SCRIPTS:
        return False
    ratio = c.get(want, 0) / letters
    return ratio >= _KEEP_RATIO_CJK


def is_cjk_lang(lang: str) -> bool:
    return normalize_code(lang) in tuple(normalize_code(x) for x in _CJK_LANGS)
