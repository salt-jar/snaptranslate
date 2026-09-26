# -*- coding: utf-8 -*-
"""翻译引擎基类、HTTP 工具与文本分段。"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
_SSL = ssl.create_default_context()


class ProviderError(RuntimeError):
    """可展示给用户的翻译错误。"""


@dataclass
class TranslateResult:
    text: str
    engine: str
    elapsed: float
    detected: str = ""
    note: str = ""


# --------------------------------------------------------------------- HTTP


def http_json(url: str, method: str = "GET", payload: Optional[dict] = None,
              headers: Optional[dict] = None, timeout: float = 12.0,
              form: Optional[dict] = None) -> Any:
    """发一个请求并解析 JSON。失败抛 :class:`ProviderError`（带中文说明）。"""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"}
    hdrs.update(headers or {})
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        raise ProviderError("服务器返回 %s%s" % (e.code, ("：" + body) if body else "")) from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise ProviderError("网络连接失败（%s）" % reason) from e
    except TimeoutError as e:
        raise ProviderError("请求超时") from e

    text = raw.decode("utf-8", "replace").strip()
    if not text:
        raise ProviderError("服务器返回了空内容")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ProviderError("返回内容不是合法 JSON：%s" % text[:120]) from e


def http_text(url: str, method: str = "GET", payload: Optional[dict] = None,
              headers: Optional[dict] = None, timeout: float = 12.0,
              form: Optional[dict] = None) -> str:
    hdrs = {"User-Agent": USER_AGENT}
    hdrs.update(headers or {})
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ProviderError("服务器返回 %s" % e.code) from e
    except urllib.error.URLError as e:
        raise ProviderError("网络连接失败（%s）" % getattr(e, "reason", e)) from e


# --------------------------------------------------------------------- 分段

#: 句末标点，只用于「超长单行」的折行，**不用于跨行切分**
_SENT_END = re.compile(r"[^。！？!?…；;.]*[。！？!?…；;.]\s*")


def _split_long_line(line: str, limit: int) -> List[str]:
    """把超过 ``limit`` 的单行按句子边界切开（无损），句子仍超长的再硬切。"""
    pieces = [m.group(0) for m in _SENT_END.finditer(line)]
    consumed = sum(len(p) for p in pieces)
    if consumed < len(line):
        pieces.append(line[consumed:])

    out: List[str] = []
    cur = ""
    for p in pieces:
        if len(p) > limit:
            if cur:
                out.append(cur)
                cur = ""
            for i in range(0, len(p), limit):
                out.append(p[i:i + limit])
            continue
        if cur and len(cur) + len(p) > limit:
            out.append(cur)
            cur = ""
        cur += p
    if cur:
        out.append(cur)
    return out


def chunk_text(text: str, limit: int) -> List[str]:
    """按**行边界**把文本切成不超过 ``limit`` 字符的片段。

    这里修掉的是「长文本丢行结构」这个 bug：旧实现用 ``_SENT_END`` 按句号切分，
    而正则里的 ``\\s*`` 会把句号后面的换行一并吃掉，于是重新拼接后
    实测出现 **30 行 → 1 行**（文本超过 ``max_chunk`` 才会触发切分，
    所以短文本看起来是正常的，问题只在长文本上暴露）。

    现在只在行边界切分，行内的换行原样保留。调用方按 ``"\\n".join(chunks)``
    拼回即可还原行结构 —— 实测有道与 Yandex 对多行输入都会保留内部换行。

    唯一例外是单行本身就超过 ``limit`` 的情况（截图 OCR 几乎不会出现），
    那时会在句子边界折断，拼回时多出一个换行。
    """
    text = text or ""
    if not text:
        return []
    if limit <= 0 or len(text) <= limit:
        return [text]

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    def flush() -> None:
        nonlocal cur, cur_len
        if cur:
            chunks.append("\n".join(cur))
            cur = []
            cur_len = 0

    for line in text.split("\n"):
        if len(line) > limit:
            flush()
            chunks.extend(_split_long_line(line, limit))
            continue
        extra = len(line) + (1 if cur else 0)
        if cur and cur_len + extra > limit:
            flush()
            extra = len(line)
        cur.append(line)
        cur_len += extra
    flush()

    kept = [c for c in chunks if c.strip()]
    return kept or [text]


# --------------------------------------------------------------------- 基类


class Provider:
    """所有翻译引擎的基类。

    子类至少要实现 :meth:`translate_chunk`；分段、重试、进度由基类负责。
    """

    key: str = "base"
    label: str = "基础引擎"
    detail: str = ""
    max_chunk: int = 1400
    #: 需要用户在设置里填写 Key 才算可用
    requires_key: bool = False

    def __init__(self, cfg: dict):
        self.cfg = dict(cfg or {})
        self.timeout = float(self.cfg.get("timeout", 12) or 12)

    # ---------------------------------------------------------------- 可用性

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return True, ""

    # ---------------------------------------------------------------- 翻译

    def translate_chunk(self, text: str, src: str, dst: str) -> str:
        raise NotImplementedError

    def translate(self, text: str, src: str, dst: str,
                  progress=None) -> Tuple[str, str]:
        """返回 ``(译文, 检测到的源语言)``。

        分段之间用换行拼接：``chunk_text`` 只在行边界切分，
        所以这样拼回来能还原原文的行结构。
        """
        text = (text or "").strip()
        if not text:
            return "", ""
        limit = max(200, int(self.cfg.get("max_chunk", self.max_chunk) or self.max_chunk))
        chunks = chunk_text(text, limit)
        out: List[str] = []
        detected = ""
        for i, ch in enumerate(chunks):
            if progress:
                progress(i, len(chunks))
            piece = self.translate_chunk(ch, src, dst)
            if isinstance(piece, tuple):
                piece, lang = piece
                detected = detected or (lang or "")
            out.append(piece)
        return "\n".join(out).strip(), detected


def _is_cjk(lang: str) -> bool:
    return lang in ("zh-CHS", "zh-CHT", "ja", "ko")


def now() -> float:
    return time.perf_counter()
