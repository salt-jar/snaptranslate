# -*- coding: utf-8 -*-
"""本地离线翻译引擎。

直接用 CTranslate2 + SentencePiece 跑 OPUS-MT 模型，不经过 argostranslate：
依赖少（44MB vs 约 200MB）、可控、而且**下载完语言包之后全程不再联网**。

解码那一行 ``▁`` 处理是跟 argostranslate 学的，它源码里写得很清楚：

    # Replace SentencePiece space marker ▁ (U+2581) and regular underscores with spaces
    # （注释还特意提到：不做这步对亚洲语言的翻译结果"quite detrimental"）

原因是这类模型的 CTranslate2 词表（shared_vocabulary.json）比
sentencepiece.model 的词表大（65000 vs 32000），目标侧有些 token 不在
分词器词表里，``decode_pieces`` 会原样返回，必须自己把空格标记还原。
"""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .. import offline
from .base import Provider, ProviderError, chunk_text

#: 一个语言包的最大输入长度（OPUS-MT 上限 512 token，中文约 1 字 1 token）
MAX_CHUNK = 380

#: 最多同时缓存几个模型（每个约占 80MB 内存）
MAX_CACHED_MODELS = 2

#: 内部语言代码 -> argos 语言代码
_TO_ARGOS = {
    "zh-CHS": "zh", "zh-CHT": "zt",
    "ja": "ja", "ko": "ko", "fr": "fr", "de": "de", "es": "es", "ru": "ru",
    "pt": "pt", "it": "it", "nl": "nl", "pl": "pl", "tr": "tr", "ar": "ar",
    "th": "th", "vi": "vi", "id": "id", "ms": "ms", "hi": "hi", "uk": "uk",
    "cs": "cs", "sv": "sv", "he": "he", "el": "el", "en": "en",
}


def to_argos(code: str) -> str:
    return _TO_ARGOS.get(code, code)


# --------------------------------------------------------------------- 依赖


def missing_deps() -> List[str]:
    out = []
    for mod, pkg in (("ctranslate2", "ctranslate2"), ("sentencepiece", "sentencepiece")):
        try:
            __import__(mod)
        except Exception:
            out.append(pkg)
    return out


def engine_ready() -> Tuple[bool, str]:
    miss = missing_deps()
    if miss:
        return False, "缺少依赖：%s（运行 安装依赖.bat）" % "、".join(miss)
    pairs = offline.installed_pairs()
    if not pairs:
        return False, "尚未下载任何离线语言包"
    return True, "已安装 %d 个语言包" % len(pairs)


# --------------------------------------------------------------------- 模型缓存

_lock = threading.RLock()
_cache: "OrderedDict[str, Tuple[object, object]]" = OrderedDict()   # key -> (translator, sp)

#: 保护 os.chdir。见 _load_objects() 里的说明。
_cwd_lock = threading.Lock()


def _load_objects(model_dir: Path, device: str, compute_type: str):
    """加载 CTranslate2 模型与 sentencepiece 分词器。

    **这里的 chdir 不是多余的**：sentencepiece 和 ctranslate2 的 C++ 层用的是
    窄字符文件 API，在 Windows 上遇到非 ASCII 路径会直接
    ``NOT_FOUND: "D:\\...\\翻译软件\\models\\...": No such file or directory``
    ——文件明明存在，Python 也读得到，但 C++ 层打不开。
    （实测：绝对路径失败，chdir 到目录后用相对文件名则完全正常。）

    所以：路径是纯 ASCII 时直接传绝对路径；含非 ASCII 字符时，
    临时切到模型目录、只用相对文件名加载。两个库都是在构造时把模型读进内存，
    因此 chdir 的窗口很短；其余文件操作全部走绝对路径，不受影响。
    """
    import ctranslate2
    import sentencepiece as spm

    last_err: Optional[Exception] = None
    attempts = [compute_type] if compute_type != "auto" else []
    attempts += ["int8", "auto", "float32"]

    if str(model_dir).isascii():
        translator = None
        for ct in attempts:
            try:
                translator = ctranslate2.Translator(str(model_dir / "model"),
                                                    device=device, compute_type=ct)
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
        if translator is None:
            raise ProviderError("加载离线模型失败：%s" % last_err)
        sp = spm.SentencePieceProcessor(model_file=str(model_dir / "sentencepiece.model"))
        return translator, sp

    with _cwd_lock:
        old = os.getcwd()
        try:
            os.chdir(str(model_dir))
            translator = None
            for ct in attempts:
                try:
                    translator = ctranslate2.Translator("model", device=device,
                                                        compute_type=ct)
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = e
            if translator is None:
                raise ProviderError("加载离线模型失败：%s" % last_err)
            sp = spm.SentencePieceProcessor(model_file="sentencepiece.model")
        finally:
            os.chdir(old)
    return translator, sp


def _get_model(from_code: str, to_code: str):
    """按需加载并缓存 (translator, sentencepiece)。"""
    d = offline.pack_dir(from_code, to_code)
    key = "%s_%s" % (from_code, to_code)

    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    if not (d / "model" / "model.bin").is_file():
        raise ProviderError("语言包 %s → %s 尚未安装" % (from_code, to_code))

    if missing_deps():
        raise ProviderError("离线翻译引擎不可用：缺少 %s（请运行 安装依赖.bat）"
                            % "、".join(missing_deps()))

    from ..config import config

    lcfg = config.section("translate").get("local") or {}
    device = str(lcfg.get("device") or "cpu")
    compute = str(lcfg.get("compute_type") or "int8")

    translator, sp = _load_objects(d, device, compute)

    with _lock:
        _cache[key] = (translator, sp)
        _cache.move_to_end(key)
        while len(_cache) > MAX_CACHED_MODELS:
            _old_key, (old_tr, _old_sp) = _cache.popitem(last=False)
            try:
                old_tr.unload_model()
            except Exception:
                pass
    return translator, sp


def unload_all() -> None:
    with _lock:
        for _key, (tr, _sp) in _cache.items():
            try:
                tr.unload_model()
            except Exception:
                pass
        _cache.clear()


def loaded_models() -> List[str]:
    with _lock:
        return list(_cache.keys())


# --------------------------------------------------------------------- 分词


def encode(sp, text: str) -> List[str]:
    return sp.encode(text, out_type=str)


def decode(sp, tokens: List[str]) -> str:
    """还原成可读文本。

    必须自己处理空格标记：目标侧有一部分 token 不在 sentencepiece 词表里
    （模型词表 65000 > 分词器词表 32000），``decode_pieces`` 会原样吐回
    ``▁Hello`` 这种东西。argostranslate 也是这么补的。
    """
    text = sp.decode(tokens)
    if "\u2581" in text:
        text = text.replace("\u2581", " ")
    elif "_" in text:
        # 少数模型用下划线作词间标记（argos 的注释里也提到了这一种）
        text = text.replace("_", " ")
    text = text.replace("\u2047", "")       # sentencepiece 的 <unk> 占位符
    return " ".join(text.split())


# --------------------------------------------------------------------- 语种识别


def _script_of(text: str) -> str:
    counts = {"han": 0, "kana": 0, "hangul": 0, "cyrillic": 0, "latin": 0,
              "arabic": 0, "thai": 0}
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            counts["han"] += 1
        elif 0x3040 <= o <= 0x30FF:
            counts["kana"] += 1
        elif 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            counts["hangul"] += 1
        elif 0x0400 <= o <= 0x04FF:
            counts["cyrillic"] += 1
        elif 0x0600 <= o <= 0x06FF:
            counts["arabic"] += 1
        elif 0x0E00 <= o <= 0x0E7F:
            counts["thai"] += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            counts["latin"] += 1

    if counts["kana"] > 0:
        return "ja"
    if counts["hangul"] > 0:
        return "ko"
    if counts["han"] > 0:
        return "zh"
    if counts["cyrillic"] > counts["latin"]:
        return "ru"
    if counts["arabic"] > 0:
        return "ar"
    if counts["thai"] > 0:
        return "th"
    return "en"


def detect(text: str) -> str:
    """返回 argos 语言代码。判断不了就当作英语。"""
    return _script_of(text or "")


# --------------------------------------------------------------------- 引擎


def resolve_chain(src: str, dst: str) -> List[Tuple[str, str]]:
    """找出可用的翻译路径，必要时经英语中转（argos 也是这么做的）。"""
    installed = set(offline.installed_pairs().keys())
    if (src, dst) in installed:
        return [(src, dst)]
    if src != "en" and dst != "en":
        if (src, "en") in installed and ("en", dst) in installed:
            return [(src, "en"), ("en", dst)]
    if (src, "en") in installed:
        return [(src, "en")]
    if ("en", dst) in installed:
        return [("en", dst)]
    raise ProviderError(
        "没有 %s → %s 的离线语言包。请到「设置 → 翻译引擎 → 管理离线语言包」下载。"
        % (offline.lang_name(src), offline.lang_name(dst))
    )


class LocalProvider(Provider):
    key = "local"
    label = "本地离线翻译（需下载语言包）"
    detail = "完全在本机运行，文本不离开电脑；不会产生任何网络请求"
    max_chunk = MAX_CHUNK
    requires_key = False

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self._lcfg = dict((cfg or {}).get("local") or {})

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return engine_ready()

    # ---------------------------------------------------------------- 翻译

    def _run_hop(self, src: str, dst: str, text: str) -> str:
        translator, sp = _get_model(src, dst)
        beam = int(self._lcfg.get("beam_size", 1) or 1)
        tokens = encode(sp, text)
        if not tokens:
            return ""
        try:
            results = translator.translate_batch([tokens], beam_size=beam)
        except Exception as e:  # noqa: BLE001
            raise ProviderError("离线推理失败：%s" % e) from e
        if not results or not results[0].hypotheses:
            return ""
        return decode(sp, results[0].hypotheses[0])

    def _run_hop_batch(self, src: str, dst: str, texts: List[str]) -> List[str]:
        """一次翻译多段（截图场景下每一行算一段）。

        批量调用的好处不只是快：neural MT 对"一行一句"的输入效果明显好于
        把整段揉成一句，而且能让译文保持与原文相同的行结构——
        截图翻译里这个很重要，否则多行会被压成一整段。
        """
        if not texts:
            return []
        beam = int(self._lcfg.get("beam_size", 1) or 1)
        out: List[str] = [""] * len(texts)
        short_idx, long_idx = [], []
        for i, t in enumerate(texts):
            (long_idx if len(t) > MAX_CHUNK else short_idx).append(i)

        if short_idx:
            translator, sp = _get_model(src, dst)
            batch = [encode(sp, texts[i]) for i in short_idx]
            try:
                results = translator.translate_batch(batch, beam_size=beam)
            except Exception as e:  # noqa: BLE001
                raise ProviderError("离线推理失败：%s" % e) from e
            for i, r in zip(short_idx, results):
                out[i] = decode(sp, r.hypotheses[0]) if r.hypotheses else ""

        # 超长的行单独切段处理
        for i in long_idx:
            parts = chunk_text(texts[i], MAX_CHUNK) or [texts[i]]
            pieces = self._run_hop_batch(src, dst, parts)
            out[i] = "".join(pieces) if dst in ("zh", "zt", "ja", "ko") else " ".join(pieces)
        return out

    def translate_chunk(self, text: str, src: str, dst: str):
        a, b = to_argos(src), to_argos(dst)
        chain = resolve_chain(a, b)
        out = text
        for hop_from, hop_to in chain:
            pieces: List[str] = []
            for part in chunk_text(out, MAX_CHUNK) or [out]:
                pieces.append(self._run_hop(hop_from, hop_to, part))
            out = ("".join(pieces) if hop_to in ("zh", "zt", "ja", "ko")
                   else " ".join(p for p in pieces if p))
        return out.strip(), ("zh-CHS" if a == "zh" else a)

    def translate(self, text: str, src: str, dst: str, progress=None):
        """覆盖基类：按行翻译并保留行结构，语种识别与路径解析只做一次。"""
        text = (text or "").strip()
        if not text:
            return "", ""

        real_src = to_argos(src) if src not in ("", "auto") else detect(text)
        real_dst = to_argos(dst)
        if real_src == real_dst:
            return text, src

        chain = resolve_chain(real_src, real_dst)

        # 按行拆成一个一个翻译单元；空行丢弃，靠换行符还原结构
        units = [ln.strip() for ln in text.split("\n") if ln.strip()] or [text]
        if progress:
            progress(0, len(chain))

        for i, (hop_from, hop_to) in enumerate(chain):
            if progress:
                progress(i, len(chain), 0, len(units))
            units = self._run_hop_batch(hop_from, hop_to, units)

        out = "\n".join(u for u in units if u)
        detected = {"zh": "zh-CHS", "zt": "zh-CHT"}.get(real_src, real_src)
        return out.strip(), detected
