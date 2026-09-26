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

_SENT_END = re.compile(r"(?<=[。！？!?…；;\.])\s*")


def chunk_text(text: str, limit: int) -> List[str]:
    """按句子边界把长文本切成不超过 ``limit`` 字符的片段。"""
    text = text or ""
    if limit <= 0 or len(text) <= limit:
        return [text] if text else []

    pieces: List[str] = []
    for part in _SENT_END.split(text):
        if not part:
            continue
        if len(part) <= limit:
            pieces.append(part)
            continue
        # 单句就超长：先按换行，再硬切
        for line in part.split("\n"):
            if len(line) <= limit:
                pieces.append(line + "\n")
            else:
                for i in range(0, len(line), limit):
                    pieces.append(line[i:i + limit])
    chunks: List[str] = []
    cur = ""
    for p in pieces:
        if cur and len(cur) + len(p) > limit:
            chunks.append(cur)
            cur = ""
        cur += p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()]


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
        """返回 ``(译文, 检测到的源语言)``。"""
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
            piece, lang = self.translate_chunk(ch, src, dst), ""
            if isinstance(piece, tuple):
                piece, lang = piece
            detected = detected or lang or ""
            out.append(piece)
        joiner = "" if _is_cjk(dst) else " "
        return joiner.join(out).strip(), detected


def _is_cjk(lang: str) -> bool:
    return lang in ("zh-CHS", "zh-CHT", "ja", "ko")


def now() -> float:
    return time.perf_counter()
