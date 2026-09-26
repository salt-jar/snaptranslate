# -*- coding: utf-8 -*-
"""翻译门面：引擎注册、自动容错、结果缓存。

对上层只暴露一个 :func:`translate`，它负责：

1. 命中缓存直接返回；
2. 按用户选择的引擎翻译；
3. 失败且开启了「自动容错」时，依次尝试其它可用引擎；
4. 把最终使用的引擎、耗时、检测到的语言一并返回。
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple

from ..cache import LRUCache
from .base import Provider, ProviderError, TranslateResult, chunk_text  # noqa: F401
from .custom import CustomProvider
from .free import GoogleFreeProvider, MyMemoryProvider, YandexProvider, YoudaoFreeProvider
from .llm import LlmProvider
from .local import LocalProvider
from .official import BaiduProvider, YoudaoOfficialProvider

PROVIDERS: List[type] = [
    YandexProvider,
    YoudaoFreeProvider,
    MyMemoryProvider,
    GoogleFreeProvider,
    LocalProvider,
    LlmProvider,
    BaiduProvider,
    YoudaoOfficialProvider,
    CustomProvider,
]
_BY_KEY: Dict[str, type] = {p.key: p for p in PROVIDERS}

#: 自动容错的尝试顺序（都是免 Key 引擎，保证一定可试）。
#: 注意这里**不包含** local：本地翻译是用户为隐私特意选的，
#: 不能因为失败就偷偷把文本发到网上，见 _candidates()。
FALLBACK_ORDER = ["youdao_free", "yandex", "mymemory", "google_free"]

#: 有道免密只支持中英，其它目标语言时把它排到最后
_YOUDAO_TARGETS = {"zh-CHS", "en"}

_cache = LRUCache(300)


def set_cache_size(size: int) -> None:
    _cache.resize(max(10, int(size)))


def clear_cache() -> None:
    _cache.clear()


def list_providers() -> List[Tuple[str, str]]:
    out = [("auto", "智能选择（自动容错，推荐）")]
    for p in PROVIDERS:
        out.append((p.key, p.label))
    return out


def provider_status(cfg: dict) -> Dict[str, str]:
    st: Dict[str, str] = {}
    for p in PROVIDERS:
        try:
            ok, reason = p.available(cfg)
        except Exception as e:  # noqa: BLE001
            ok, reason = False, str(e)[:80]
        st[p.key] = "可用" if ok else ("未配置：" + reason)
    return st


def make_provider(key: str, cfg: dict) -> Provider:
    cls = _BY_KEY.get(key)
    if cls is None:
        raise ProviderError("未知的翻译引擎：%s" % key)
    ok, reason = cls.available(cfg)
    if not ok:
        raise ProviderError("%s 不可用：%s" % (cls.label, reason))
    return cls(cfg)


def auto_order(dst: str) -> List[str]:
    if dst in _YOUDAO_TARGETS:
        return list(FALLBACK_ORDER)
    return [k for k in FALLBACK_ORDER if k != "youdao_free"] + ["youdao_free"]


def _candidates(engine: str, dst: str, fallback: bool) -> List[str]:
    # 本地离线翻译绝不做在线兜底：用户选它就是为了"文本不出本机"，
    # 一旦失败就转投在线引擎，等于把隐私保护偷偷取消了。
    if engine == "local":
        return ["local"]

    chain = auto_order(dst)
    if engine and engine != "auto":
        if not fallback:
            return [engine]
        return [engine] + [k for k in chain if k != engine]
    return chain


def _normalize_for_compare(text: str) -> str:
    return "".join((text or "").split()).lower()


def _flip_target(dst: str) -> str:
    return "en" if str(dst).startswith("zh") else "zh-CHS"


def _needs_flip(source: str, result: TranslateResult, src: str, dst: str,
                auto_target: bool = False) -> bool:
    """判断是否需要反向翻译。

    典型场景：用户选了「译成中文」，但截图里本来就是中文——引擎会原样返回，
    界面上看起来就像坏了。这时自动改成译成英文，结果才有用。
    """
    if src not in ("", "auto"):
        return False                      # 用户明确指定了源语言，尊重其选择
    detected = (result.detected or "").strip().lower()
    unchanged = _normalize_for_compare(result.text) == _normalize_for_compare(source)
    if auto_target:
        # 目标语言是「自动」时，先按中文试；只有原文确实是中文才需要改译英文
        return unchanged or detected.startswith("zh")
    if detected and detected == dst:
        return True
    return unchanged


def translate(text: str, src: str, dst: str, cfg: dict,
              progress: Optional[Callable[[int, int], None]] = None,
              use_cache: bool = True, _flipped: bool = False) -> TranslateResult:
    """翻译一段文本。异常情况抛 :class:`ProviderError`（消息可直接展示）。"""
    tcfg = dict(cfg or {})
    text = (text or "").strip()
    if not text:
        return TranslateResult("", "", 0.0)

    # 「自动」目标语言：先按译成中文试，若原文本来就是中文再改译英文
    auto_target = str(dst) == "auto"
    if auto_target:
        dst = "zh-CHS"

    engine = str(tcfg.get("engine") or "auto")
    fallback = bool(tcfg.get("fallback", True))
    chain = _candidates(engine, dst, fallback)
    if not chain:
        raise ProviderError("没有可用的翻译引擎")

    cache_key = None
    if use_cache:
        cache_key = (engine, src, dst, text)
        hit = _cache.get(cache_key)
        if hit is not None:
            hit_result = TranslateResult(hit[0], hit[1], 0.0, hit[2], note="（缓存）")
            if not _flipped and _needs_flip(text, hit_result, src, dst, auto_target):
                return _do_flip(text, src, dst, tcfg, progress, auto_target)
            return hit_result

    t0 = time.perf_counter()
    errors: List[str] = []
    for i, key in enumerate(chain):
        cls = _BY_KEY.get(key)
        if cls is None:
            continue
        try:
            ok, reason = cls.available(tcfg)
            if not ok:
                errors.append("%s：%s" % (cls.label, reason))
                continue
            provider = cls(tcfg)
            out, detected = provider.translate(text, src, dst, progress=progress)
            elapsed = time.perf_counter() - t0
            if not out.strip():
                errors.append("%s：返回空译文" % cls.label)
                continue
            note = ""
            if i > 0:
                note = "已自动切换到「%s」" % cls.label
            if cache_key is not None:
                _cache.put(cache_key, (out, cls.key, detected))
            result = TranslateResult(out, cls.key, elapsed, detected, note)
            if not _flipped and _needs_flip(text, result, src, dst, auto_target):
                return _do_flip(text, src, dst, tcfg, progress, auto_target)
            return result
        except ProviderError as e:
            errors.append("%s：%s" % (cls.label, e))
        except Exception as e:  # noqa: BLE001
            errors.append("%s：%s: %s" % (cls.label, type(e).__name__, str(e)[:120]))

    raise ProviderError("翻译失败。\n" + "\n".join("· " + e for e in errors[:5]))


def _do_flip(text: str, src: str, dst: str, tcfg: dict,
             progress, auto_target: bool) -> TranslateResult:
    """反向重译一次（中文 <-> 英文）。"""
    flipped = _flip_target(dst)
    try:
        result = translate(text, src, flipped, tcfg, progress=progress,
                           use_cache=True, _flipped=True)
    except ProviderError:
        # 反向失败就退回原结果，不要让用户什么都看不到
        raise
    if auto_target:
        result.note = ("原文已是中文，已自动译为英文"
                       if flipped == "en" else "已自动译为中文")
    else:
        result.note = "原文已是目标语言，已自动反向译为「%s」" % flipped
    return result


def engine_label(key: str) -> str:
    cls = _BY_KEY.get(key)
    return cls.label if cls else (key or "未知")
