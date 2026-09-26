# -*- coding: utf-8 -*-
"""需要用户自己申请 Key 的官方翻译 API：百度、有道智云。"""
from __future__ import annotations

import hashlib
import time
from typing import Tuple

from ..langs import to_baidu
from .base import Provider, ProviderError, http_json

# --------------------------------------------------------------------- 百度


class BaiduProvider(Provider):
    key = "baidu"
    label = "百度翻译开放平台（需 Key）"
    detail = "需在 fanyi-api.baidu.com 申请 APPID 与密钥；标准版每月有免费额度"
    requires_key = True
    max_chunk = 2000

    URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        c = (cfg or {}).get("baidu") or {}
        if not str(c.get("appid") or "").strip():
            return False, "未填写 APPID"
        if not str(c.get("key") or "").strip():
            return False, "未填写密钥"
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        c = self.cfg.get("baidu") or {}
        appid = str(c.get("appid") or "").strip()
        key = str(c.get("key") or "").strip()
        salt = str(int(time.time() * 1000))
        sign = hashlib.md5((appid + text + salt + key).encode("utf-8")).hexdigest()
        data = http_json(self.URL, method="POST", form={
            "q": text, "from": to_baidu(src), "to": to_baidu(dst),
            "appid": appid, "salt": salt, "sign": sign,
        }, timeout=self.timeout)

        if data.get("error_code"):
            raise ProviderError("百度翻译错误 %s：%s"
                                % (data.get("error_code"), data.get("error_msg", "")))
        rows = data.get("trans_result") or []
        out = "\n".join(str(r.get("dst", "")) for r in rows)
        if not out.strip():
            raise ProviderError("百度翻译返回空结果")
        return out, ""


# --------------------------------------------------------------------- 有道智云


class YoudaoOfficialProvider(Provider):
    key = "youdao_official"
    label = "有道智云（需 Key）"
    detail = "需在 ai.youdao.com 创建应用，拿到应用 ID 与应用密钥"
    requires_key = True
    max_chunk = 2000

    URL = "https://openapi.youdao.com/api"

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        c = (cfg or {}).get("youdao_official") or {}
        if not str(c.get("appkey") or "").strip():
            return False, "未填写应用 ID"
        if not str(c.get("secret") or "").strip():
            return False, "未填写应用密钥"
        return True, ""

    @staticmethod
    def _truncate(q: str) -> str:
        if len(q) <= 20:
            return q
        return q[:10] + str(len(q)) + q[-10:]

    def translate_chunk(self, text: str, src: str, dst: str):
        c = self.cfg.get("youdao_official") or {}
        appkey = str(c.get("appkey") or "").strip()
        secret = str(c.get("secret") or "").strip()
        salt = str(int(time.time() * 1000))
        curtime = str(int(time.time()))
        sign = hashlib.sha256(
            (appkey + self._truncate(text) + salt + curtime + secret).encode("utf-8")
        ).hexdigest()

        data = http_json(self.URL, method="POST", form={
            "q": text, "from": src, "to": dst, "appKey": appkey, "salt": salt,
            "sign": sign, "signType": "v3", "curtime": curtime,
        }, timeout=self.timeout)

        code = str(data.get("errorCode", "0"))
        if code != "0":
            raise ProviderError("有道智云错误 %s" % code)
        parts = data.get("translation") or []
        out = "\n".join(str(p) for p in parts)
        if not out.strip():
            raise ProviderError("有道智云返回空结果")
        return out, ""
