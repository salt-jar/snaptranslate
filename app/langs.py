# -*- coding: utf-8 -*-
"""语言代码表与各家翻译引擎的代码映射。"""
from __future__ import annotations

from typing import List, Tuple

# 内部统一使用有道风格的代码：auto / zh-CHS / zh-CHT / en / ja ...
LANGS: List[Tuple[str, str]] = [
    ("auto", "自动检测"),
    ("zh-CHS", "中文（简体）"),
    ("zh-CHT", "中文（繁体）"),
    ("en", "英语"),
    ("ja", "日语"),
    ("ko", "韩语"),
    ("fr", "法语"),
    ("de", "德语"),
    ("es", "西班牙语"),
    ("ru", "俄语"),
    ("pt", "葡萄牙语"),
    ("it", "意大利语"),
    ("nl", "荷兰语"),
    ("pl", "波兰语"),
    ("tr", "土耳其语"),
    ("ar", "阿拉伯语"),
    ("th", "泰语"),
    ("vi", "越南语"),
    ("id", "印尼语"),
    ("ms", "马来语"),
    ("hi", "印地语"),
    ("uk", "乌克兰语"),
    ("cs", "捷克语"),
    ("sv", "瑞典语"),
    ("he", "希伯来语"),
    ("el", "希腊语"),
]

_LABEL = dict(LANGS)

#: 目标语言下拉框用：多一个「自动」——中文原文自动译成英文，其它语言译成中文
TARGETS: List[Tuple[str, str]] = [("auto", "自动（中文→英文，其它→中文）")] + [
    (code, name) for code, name in LANGS if code != "auto"
]


def label(code: str) -> str:
    return _LABEL.get(code, code or "未知")


def display_name(code: str, max_len: int = 6) -> str:
    """用于按钮上的短名，例如 中文（简体） -> 简体中文。"""
    short = {
        "auto": "自动",
        "zh-CHS": "中文",
        "zh-CHT": "繁体",
        "en": "英文",
        "ja": "日文",
        "ko": "韩文",
        "fr": "法文",
        "de": "德文",
        "es": "西文",
        "ru": "俄文",
        "pt": "葡文",
        "it": "意文",
    }
    v = short.get(code)
    if v:
        return v
    n = _LABEL.get(code, code)
    return n[:max_len]


# --------------------------------------------------------------------- 各家映射

_GOOGLE = {
    "zh-CHS": "zh-CN",
    "zh-CHT": "zh-TW",
}

_MYMEMORY = {
    "zh-CHS": "zh-CN",
    "zh-CHT": "zh-TW",
}

_BAIDU = {
    "zh-CHS": "zh",
    "zh-CHT": "cht",
    "ja": "jp",
    "ko": "kor",
    "fr": "fra",
    "es": "spa",
    "ar": "ara",
    "auto": "auto",
}

_LLM_NAME = {
    "zh-CHS": "简体中文",
    "zh-CHT": "繁体中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ar": "阿拉伯语",
    "th": "泰语",
    "vi": "越南语",
}


def to_google(code: str) -> str:
    return _GOOGLE.get(code, code if code != "auto" else "auto")


def to_mymemory(code: str) -> str:
    if code == "auto":
        return "Autodetect"
    return _MYMEMORY.get(code, code)


def to_baidu(code: str) -> str:
    return _BAIDU.get(code, code)


def to_llm_name(code: str) -> str:
    if code == "auto":
        return "自动判断的目标语言（见下文）"
    return _LLM_NAME.get(code, code)


# RapidOCR / PaddleOCR 语言标识
RAPID_LANGS: List[Tuple[str, str]] = [
    ("ch", "中英混合（推荐）"),
    ("en", "纯英文"),
    ("japan", "日文"),
    ("korean", "韩文"),
    ("chinese_cht", "繁体中文"),
    ("latin", "拉丁语系"),
    ("cyrillic", "西里尔语系"),
    ("arabic", "阿拉伯语"),
    ("devanagari", "天城文"),
]
