# -*- coding: utf-8 -*-
"""语言代码表与各家翻译引擎的代码映射。

内部统一使用「有道风格」的代码：``auto`` / ``zh-CHS`` / ``zh-CHT`` /
``en`` / ``ja``…… 其它语言一律使用 ISO 639-1 两位代码。各家 API 的
差异（``zh-CN`` / ``iw`` / ``jp`` / ``nb`` 等）在 ``to_*`` 映射函数里处理。

语言列表覆盖 100+ 种在线引擎常见语言；具体某个引擎是否支持某个语种
取决于引擎本身，离线模式则取决于有没有对应的 Argos 语言包。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

#: 内部语言代码 -> 中文显示名。顺序 = 下拉框顺序：常用语言在前。
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
    # ---- 欧洲 ----
    ("da", "丹麦语"),
    ("no", "挪威语"),
    ("fi", "芬兰语"),
    ("is", "冰岛语"),
    ("hu", "匈牙利语"),
    ("ro", "罗马尼亚语"),
    ("bg", "保加利亚语"),
    ("sk", "斯洛伐克语"),
    ("sl", "斯洛文尼亚语"),
    ("hr", "克罗地亚语"),
    ("bs", "波斯尼亚语"),
    ("sr", "塞尔维亚语"),
    ("mk", "马其顿语"),
    ("sq", "阿尔巴尼亚语"),
    ("et", "爱沙尼亚语"),
    ("lv", "拉脱维亚语"),
    ("lt", "立陶宛语"),
    ("ga", "爱尔兰语"),
    ("cy", "威尔士语"),
    ("gd", "苏格兰盖尔语"),
    ("lb", "卢森堡语"),
    ("mt", "马耳他语"),
    ("ca", "加泰罗尼亚语"),
    ("gl", "加利西亚语"),
    ("eu", "巴斯克语"),
    ("eo", "世界语"),
    ("la", "拉丁语"),
    ("af", "南非荷兰语"),
    ("fy", "弗里西语"),
    # ---- 中东 / 中亚 / 高加索 ----
    ("fa", "波斯语"),
    ("ur", "乌尔都语"),
    ("ps", "普什图语"),
    ("ku", "库尔德语"),
    ("az", "阿塞拜疆语"),
    ("kk", "哈萨克语"),
    ("ky", "吉尔吉斯语"),
    ("uz", "乌兹别克语"),
    ("tg", "塔吉克语"),
    ("tk", "土库曼语"),
    ("be", "白俄罗斯语"),
    ("hy", "亚美尼亚语"),
    ("ka", "格鲁吉亚语"),
    ("mn", "蒙古语"),
    ("am", "阿姆哈拉语"),
    # ---- 南亚 ----
    ("bn", "孟加拉语"),
    ("pa", "旁遮普语"),
    ("gu", "古吉拉特语"),
    ("mr", "马拉地语"),
    ("ne", "尼泊尔语"),
    ("si", "僧伽罗语"),
    ("ta", "泰米尔语"),
    ("te", "泰卢固语"),
    ("kn", "卡纳达语"),
    ("ml", "马拉雅拉姆语"),
    ("sd", "信德语"),
    ("as", "阿萨姆语"),
    # ---- 东南亚 / 东亚 ----
    ("tl", "菲律宾语"),
    ("my", "缅甸语"),
    ("km", "高棉语"),
    ("lo", "老挝语"),
    ("jv", "爪哇语"),
    ("su", "巽他语"),
    ("ceb", "宿务语"),
    ("hmn", "苗语"),
    # ---- 非洲 / 其它 ----
    ("sw", "斯瓦希里语"),
    ("so", "索马里语"),
    ("ha", "豪萨语"),
    ("ig", "伊博语"),
    ("yo", "约鲁巴语"),
    ("zu", "祖鲁语"),
    ("xh", "科萨语"),
    ("st", "塞索托语"),
    ("sn", "绍纳语"),
    ("rw", "卢旺达语"),
    ("mg", "马尔加什语"),
    ("ny", "齐切瓦语"),
    ("ht", "海地克里奥尔语"),
    ("haw", "夏威夷语"),
    ("mi", "毛利语"),
    ("sm", "萨摩亚语"),
    ("co", "科西嘉语"),
    ("yi", "意第绪语"),
]

_LABEL: Dict[str, str] = dict(LANGS)

#: 目标语言下拉框用：包含「自动」——中文原文自动译成英文，其它语言译成中文。
TARGETS: List[Tuple[str, str]] = [
    ("auto", "自动（中文→英文，其它→中文）")
] + [(code, name) for code, name in LANGS if code != "auto"]


# --------------------------------------------------------------------- 代码归一化

#: 引擎返回的代码可能是 zh-CN / iw / jp / kor / nob …… 统一转成内部代码。
_ALIASES: Dict[str, str] = {
    "zh": "zh-CHS", "zh-cn": "zh-CHS", "zh-hans": "zh-CHS",
    "zh-sg": "zh-CHS", "zh-chs": "zh-CHS", "zho": "zh-CHS", "chi": "zh-CHS",
    "cmn": "zh-CHS",
    "zh-tw": "zh-CHT", "zh-hk": "zh-CHT", "zh-hant": "zh-CHT",
    "zh-cht": "zh-CHT", "zt": "zh-CHT",
    "iw": "he", "heb": "he",
    "jw": "jv", "jav": "jv",
    "nb": "no", "nob": "no", "nno": "no", "nor": "no",
    "pb": "pt", "pt-br": "pt", "pt-pt": "pt", "por": "pt",
    "jp": "ja", "jpn": "ja",
    "kor": "ko",
    "fra": "fr", "fre": "fr",
    "deu": "de", "ger": "de",
    "spa": "es",
    "rus": "ru",
    "ita": "it",
    "nld": "nl", "dut": "nl",
    "pol": "pl",
    "tur": "tr",
    "ara": "ar",
    "tha": "th",
    "vie": "vi",
    "ind": "id",
    "msa": "ms", "may": "ms",
    "hin": "hi",
    "ukr": "uk",
    "ces": "cs", "cze": "cs",
    "swe": "sv",
    "ell": "el", "gre": "el",
    "dan": "da",
    "fin": "fi",
    "isl": "is", "ice": "is",
    "hun": "hu",
    "ron": "ro", "rum": "ro",
    "bul": "bg",
    "slk": "sk", "slo": "sk",
    "slv": "sl",
    "hrv": "hr",
    "bos": "bs",
    "srp": "sr",
    "mkd": "mk", "mac": "mk",
    "alb": "sq", "sqi": "sq",
    "est": "et",
    "lav": "lv",
    "lit": "lt",
    "gle": "ga", "iri": "ga",
    "cym": "cy", "wel": "cy",
    "gla": "gd",
    "ltz": "lb",
    "mlt": "mt",
    "cat": "ca",
    "glg": "gl",
    "eus": "eu", "baq": "eu",
    "epo": "eo",
    "lat": "la",
    "afr": "af",
    "fry": "fy",
    "fas": "fa", "per": "fa",
    "urd": "ur",
    "pus": "ps",
    "kur": "ku",
    "aze": "az",
    "kaz": "kk",
    "kir": "ky",
    "uzb": "uz",
    "tgk": "tg",
    "tuk": "tk",
    "bel": "be",
    "hye": "hy", "arm": "hy",
    "kat": "ka", "geo": "ka",
    "mon": "mn",
    "amh": "am",
    "ben": "bn",
    "pan": "pa",
    "guj": "gu",
    "mar": "mr",
    "nep": "ne",
    "sin": "si",
    "tam": "ta",
    "tel": "te",
    "kan": "kn",
    "mal": "ml",
    "snd": "sd",
    "asm": "as",
    "tgl": "tl", "fil": "tl",
    "mya": "my", "bur": "my",
    "khm": "km",
    "lao": "lo",
    "sun": "su",
    "ceb": "ceb",
    "hmn": "hmn",
    "swa": "sw",
    "som": "so",
    "hau": "ha",
    "ibo": "ig",
    "yor": "yo",
    "zul": "zu",
    "xho": "xh",
    "sot": "st",
    "sna": "sn",
    "kin": "rw",
    "mlg": "mg",
    "nya": "ny",
    "hat": "ht",
    "haw": "haw",
    "mri": "mi", "mao": "mi",
    "smo": "sm",
    "cos": "co",
    "yid": "yi",
}


def normalize_code(code: str) -> str:
    """把各种写法的语言代码转成内部代码（保留 ``zh-CHS`` / ``zh-CHT`` 大小写）。"""
    s = (code or "").strip().lower().replace("_", "-")
    if not s:
        return ""
    if s in _ALIASES:
        return _ALIASES[s]
    # en-US / fr-CA / sr-Latn 这类带地区的代码：有基础语言就退回基础语言
    if "-" in s:
        base = s.split("-", 1)[0]
        if base in _ALIASES:
            return _ALIASES[base]
        if base in _LABEL:
            return base
    return s


def label(code: str) -> str:
    if not code:
        return "未知"
    return _LABEL.get(normalize_code(code), code)


def display_name(code: str, max_len: int = 8) -> str:
    """用于按钮上的短名；没有专门短名的语言就截取显示名。"""
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
    v = short.get(normalize_code(code))
    if v:
        return v
    return label(code)[:max_len]


# --------------------------------------------------------------------- 各家映射


_GOOGLE = {
    "zh-CHS": "zh-CN",
    "zh-CHT": "zh-TW",
    "he": "iw",          # Google 的希伯来语代码仍是 iw
    "jv": "jw",          # Google 的爪哇语代码仍是 jw
}

_MYMEMORY = {
    "zh-CHS": "zh-CN",
    "zh-CHT": "zh-TW",
}

#: 百度翻译开放平台的语言代码（只列它明确支持的，未列出的直接透传，
#: 让 API 返回错误总比悄悄翻成另一种语言好）。
_BAIDU = {
    "zh-CHS": "zh",
    "zh-CHT": "cht",
    "en": "en",
    "ja": "jp",
    "ko": "kor",
    "fr": "fra",
    "de": "de",
    "es": "spa",
    "ru": "ru",
    "pt": "pt",
    "it": "it",
    "nl": "nl",
    "pl": "pl",
    "tr": "tr",
    "ar": "ara",
    "th": "th",
    "vi": "vie",
    "id": "id",
    "ms": "may",
    "hi": "hi",
    "uk": "uk",
    "cs": "cs",
    "sv": "swe",
    "he": "he",
    "el": "el",
    "da": "dan",
    "fi": "fin",
    "no": "nor",
    "hu": "hu",
    "ro": "rom",
    "bg": "bul",
    "sk": "slo",
    "et": "est",
    "auto": "auto",
}

_LLM_NAME = {code: name for code, name in LANGS if code != "auto"}


def to_google(code: str) -> str:
    code = normalize_code(code)
    if code == "auto":
        return "auto"
    return _GOOGLE.get(code, code)


def to_mymemory(code: str) -> str:
    code = normalize_code(code)
    if code == "auto":
        return "Autodetect"
    return _MYMEMORY.get(code, code)


def to_yandex(code: str) -> str:
    """Yandex 不区分简繁中文，其它代码基本与 ISO 一致。"""
    code = normalize_code(code)
    if code in ("zh-CHS", "zh-CHT"):
        return "zh"
    return code


def to_baidu(code: str) -> str:
    code = normalize_code(code)
    return _BAIDU.get(code, code)


def to_llm_name(code: str) -> str:
    code = normalize_code(code)
    if code == "auto":
        return "自动判断的目标语言（见下文）"
    return _LLM_NAME.get(code, code)


# RapidOCR / PaddleOCR 语言标识（OCR 模型自带的语言包，与翻译语种不是一回事）
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
