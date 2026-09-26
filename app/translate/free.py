# -*- coding: utf-8 -*-
"""免 Key 翻译引擎：有道 / Yandex / MyMemory / Google。

这些都是各家的公开网页接口，好处是装上就能用；
代价是有频率限制、质量与稳定性不如官方付费 API，因此程序内置了
「自动容错」——一个引擎失败会自动换下一个（见 ``app/translate/__init__.py``）。
"""
from __future__ import annotations

import threading
import time
import urllib.parse
import uuid
from typing import Optional, Tuple

from ..langs import to_google, to_mymemory
from .base import Provider, ProviderError, http_json

# --------------------------------------------------------------------- 限流器


class _Throttle:
    """保证两次请求之间至少间隔 ``interval`` 秒（同一引擎内串行）。"""

    def __init__(self, interval: float):
        self.interval = interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            gap = time.monotonic() - self._last
            if gap < self.interval:
                time.sleep(self.interval - gap)
            self._last = time.monotonic()


# --------------------------------------------------------------------- 有道


class YoudaoFreeProvider(Provider):
    key = "youdao_free"
    label = "有道翻译（免 Key）"
    detail = "免费无需配置，中英互译质量好；请求过快会短暂限流，已内置节流与重试"
    max_chunk = 1200

    URL = "https://aidemo.youdao.com/trans"
    #: 该接口目前只开放这几个目标语言
    TARGETS = {"zh-CHS", "en"}
    _throttle = _Throttle(1.2)

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        if dst not in self.TARGETS:
            raise ProviderError("有道免密接口不支持翻译成「%s」" % dst)
        src_code = src if src in ("auto", "zh-CHS", "en") else "auto"
        params = urllib.parse.urlencode({"q": text, "from": src_code, "to": dst})
        url = "%s?%s" % (self.URL, params)

        last_error: Optional[str] = None
        for attempt in range(3):
            self._throttle.wait()
            data = http_json(url, timeout=self.timeout,
                             headers={"Referer": "https://fanyi.youdao.com/"})
            code = str(data.get("errorCode", "0"))
            if code == "0":
                parts = data.get("translation") or []
                out = "\n".join(p for p in parts if p)
                if not out.strip():
                    raise ProviderError("有道返回了空的译文")
                detected = ""
                l = str(data.get("l") or "")
                if "2" in l:
                    detected = l.split("2")[0]
                return out, detected
            msg = str(data.get("msg") or "")
            last_error = "有道接口错误 %s%s" % (code, ("（%s）" % msg) if msg else "")
            if code == "411":       # 请求频率过快
                time.sleep(1.6 * (attempt + 1))
                continue
            break
        raise ProviderError(last_error or "有道翻译失败")


# --------------------------------------------------------------------- Yandex


class YandexProvider(Provider):
    key = "yandex"
    label = "Yandex 翻译（免 Key）"
    detail = "免费无需配置，支持 20+ 语种、长文本友好，是国内可直连的稳定通道"
    max_chunk = 8000

    URL = "https://translate.yandex.net/api/v1/tr.json/translate"
    _throttle = _Throttle(0.4)

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        tgt = "zh" if dst in ("zh-CHS", "zh-CHT") else dst
        lang = tgt if src in ("", "auto") else "%s-%s" % (
            "zh" if src in ("zh-CHS", "zh-CHT") else src, tgt)
        sid = str(uuid.uuid4()).replace("-", "")
        url = "%s?id=%s-0-0&srv=android" % (self.URL, sid)

        self._throttle.wait()
        data = http_json(
            url, method="POST", form={"text": text, "lang": lang},
            timeout=self.timeout,
            headers={"Referer": "https://translate.yandex.ru/"},
        )
        code = data.get("code")
        if code != 200:
            raise ProviderError("Yandex 接口错误 %s：%s"
                                % (code, str(data.get("message") or "")[:120]))
        parts = data.get("text") or []
        if not parts:
            raise ProviderError("Yandex 返回了空的译文")
        joiner = "" if tgt in ("zh", "ja", "ko") else " "
        detected = ""
        l = str(data.get("lang") or "")
        if "-" in l:
            detected = l.split("-")[0]
        return joiner.join(str(p) for p in parts), detected


# --------------------------------------------------------------------- MyMemory


class MyMemoryProvider(Provider):
    key = "mymemory"
    label = "MyMemory（免 Key）"
    detail = "免费无需配置，但单次上限 500 字符、质量一般，作为最后的兜底"
    max_chunk = 450

    URL = "https://api.mymemory.translated.net/get"

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        if len(text) > 500:
            raise ProviderError("MyMemory 单次上限 500 字符")
        pair = "%s|%s" % (to_mymemory(src) if src != "auto" else "Autodetect",
                          to_mymemory(dst))
        url = "%s?%s" % (self.URL, urllib.parse.urlencode({"q": text, "langpair": pair}))
        data = http_json(url, timeout=self.timeout)
        translated = str((data.get("responseData") or {}).get("translatedText") or "")
        status = data.get("responseStatus")
        if translated.upper().startswith("QUERY LENGTH LIMIT"):
            raise ProviderError("MyMemory 超出长度限制")
        if not translated or str(status) not in ("200", "None"):
            detail = str(data.get("responseDetails") or "")
            raise ProviderError("MyMemory 失败：%s" % (detail or status))
        return translated, ""


# --------------------------------------------------------------------- Google


class GoogleFreeProvider(Provider):
    key = "google_free"
    label = "Google 翻译（免 Key）"
    detail = "免 Key，但国内需要开启代理才能访问"
    max_chunk = 1800

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        base = str((self.cfg.get("google") or {}).get("base_url")
                   or "https://translate.googleapis.com").rstrip("/")
        url = "%s/translate_a/single?%s" % (base, urllib.parse.urlencode({
            "client": "gtx", "sl": to_google(src), "tl": to_google(dst),
            "dt": "t", "q": text,
        }))
        data = http_json(url, timeout=self.timeout)
        if not isinstance(data, list) or not data or not isinstance(data[0], list):
            raise ProviderError("Google 返回格式异常")
        out = "".join(seg[0] for seg in data[0] if seg and seg[0])
        detected = str(data[2]) if len(data) > 2 and isinstance(data[2], str) else ""
        if not out.strip():
            raise ProviderError("Google 返回了空的译文")
        return out, detected
