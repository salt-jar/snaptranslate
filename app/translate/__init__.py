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
from .glossary import Glossary
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

    注意 ``detected`` 是引擎返回的小写标记（如 ``zh-chs``），比较前必须
    把目标语言也转成小写——否则这条判断永远不成立（原来就是这个问题，
    实际只有 ``unchanged`` 那条在起作用）。
    """
    if src not in ("", "auto"):
        return False                      # 用户明确指定了源语言，尊重其选择
    detected = (result.detected or "").strip().lower()
    unchanged = _normalize_for_compare(result.text) == _normalize_for_compare(source)
    if auto_target:
        return unchanged or detected.startswith("zh")
    if detected and detected == str(dst).strip().lower():
        return True
    return unchanged


def _auto_target(text: str) -> str:
    """「自动」目标语言：**本地**按字符构成直接定方向。

    旧做法是"先按中文译一次、发现结果没变再翻转成英文"，要发两次请求；
    而且在中英混排时会整篇翻转——实测出现过「目标选中文、输出却是英文」。
    现在一次判定：几乎全是中文才译英文，其余一律译中文。
    混排的细粒度处理交给 :func:`_plan_lines`。
    """
    from .langdetect import cjk_ratio

    return "en" if cjk_ratio(text) > 0.85 else "zh-CHS"


def _plan_lines(text: str, dst: str):
    """中英混排时决定哪些行需要翻译。

    返回 ``(lines, need)``：``lines`` 是原文的所有行、``need`` 是需要翻译的
    行下标。全都要翻（或全都不用翻）时返回 ``(None, None)``，
    表示走正常的整段翻译路径。

    这一条解决的是：一张截图里既有中文又有英文时，旧实现把整段丢给引擎，
    中文行被白白翻译一遍，还常常触发"反向翻译"导致输出整体变成英文。
    """
    from .langdetect import is_target_language

    lines = text.split("\n")
    meaningful = [i for i, ln in enumerate(lines) if ln.strip()]
    need = [i for i in meaningful if not is_target_language(lines[i], dst)]
    if not need or len(need) == len(meaningful):
        return None, None
    return lines, need


def translate(text: str, src: str, dst: str, cfg: dict,
              progress: Optional[Callable[[int, int], None]] = None,
              use_cache: bool = True, _flipped: bool = False) -> TranslateResult:
    """翻译一段文本。异常情况抛 :class:`ProviderError`（消息可直接展示）。"""
    tcfg = dict(cfg or {})
    text = (text or "").strip()
    if not text:
        return TranslateResult("", "", 0.0)

    auto_target = str(dst) == "auto"
    if auto_target:
        dst = _auto_target(text)

    # ---- 混排：只把需要翻译的行送去翻译，其余原样保留 ----
    lines: Optional[List[str]] = None
    need: Optional[List[int]] = None
    payload = text
    if src in ("", "auto"):
        lines, need = _plan_lines(text, dst)
        if lines is None and not auto_target:
            # 注意：_plan_lines 只会在"全都要翻"或"全都不用翻"时返回 (None, None)，
            # 这里再确认一次是不是真的不需要翻译
            from .langdetect import is_target_language

            if all(is_target_language(ln, dst) for ln in text.split("\n")):
                if not _flipped:
                    return _do_flip(text, src, dst, tcfg, progress, auto_target)
                return TranslateResult(text, "", 0.0, "", note="原文已经是目标语言")
        elif lines is not None:
            payload = "\n".join(lines[i] for i in need or [])

    engine = str(tcfg.get("engine") or "auto")
    fallback = bool(tcfg.get("fallback", True))
    chain = _candidates(engine, dst, fallback)
    if not chain:
        raise ProviderError("没有可用的翻译引擎")

    # ---- 术语与代码保护 ----
    # config.json / PP-OCRv4 / ONNX Runtime 这类片段送进引擎会被改写或乱译，
    # 译前换成占位符、译后原样换回（详见 app/translate/glossary.py）。
    user_terms = Glossary.parse_terms(tcfg.get("glossary"))
    gl = Glossary(user_terms)
    masked, slots = gl.protect(payload)
    protected = len(slots)

    cache_key = None
    if use_cache:
        # 用户术语的"值"也要进 key：不同的译法掩码后长得一样
        cache_key = (engine, src, dst, masked, tuple(sorted(user_terms.items())))
        hit = _cache.get(cache_key)
        if hit is not None:
            hit_result = TranslateResult(hit[0], hit[1], 0.0, hit[2], note="（缓存）")
            if not _flipped and _needs_flip(payload, hit_result, src, dst, auto_target):
                return _do_flip(text, src, dst, tcfg, progress, auto_target)
            return _regroup(hit_result, lines, need)

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
            out, detected = provider.translate(masked, src, dst, progress=progress)
            elapsed = time.perf_counter() - t0
            out, lost = Glossary.restore(out, slots)
            if not out.strip():
                errors.append("%s：返回空译文" % cls.label)
                continue
            notes = []
            if i > 0:
                notes.append("已自动切换到「%s」" % cls.label)
            if lines is not None and need:
                notes.append("只翻译了 %d 行外文，其余原样保留" % len(need))
            if protected:
                survived = protected - len(lost)
                notes.append("已保护 %d 处代码/术语" % survived)
                if survived < protected:
                    notes.append("%d 处被引擎改写未能还原" % len(lost))
            result = TranslateResult(out, cls.key, elapsed, detected, " · ".join(notes))
            if cache_key is not None:
                _cache.put(cache_key, (out, cls.key, detected))
            if not _flipped and _needs_flip(payload, result, src, dst, auto_target):
                return _do_flip(text, src, dst, tcfg, progress, auto_target)
            return _regroup(result, lines, need)
        except ProviderError as e:
            errors.append("%s：%s" % (cls.label, e))
        except Exception as e:  # noqa: BLE001
            errors.append("%s：%s: %s" % (cls.label, type(e).__name__, str(e)[:120]))

    raise ProviderError("翻译失败。\n" + "\n".join("· " + e for e in errors[:5]))


def _regroup(result: TranslateResult, lines: Optional[List[str]],
             need: Optional[List[int]]) -> TranslateResult:
    """把"只翻了一部分行"的译文装回原文本。

    译文行数与送出去的行数对不上时**保持整体译文不动**——宁可丢行结构，
    也不要出现句子错位（错位比丢格式难用得多）。
    """
    if not lines or not need:
        return result
    got = result.text.split("\n")
    if len(got) != len(need):
        return result
    merged = list(lines)
    for idx, translated_line in zip(need, got):
        merged[idx] = translated_line
    result.text = "\n".join(merged)
    return result


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
