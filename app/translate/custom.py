# -*- coding: utf-8 -*-
"""自定义 HTTP 翻译接口：适配自建服务或任何未内置的翻译 API。

请求体模板可以用 ``{text}`` / ``{from}`` / ``{to}`` 占位，
响应结果用点号路径（例如 ``data.translation``）从 JSON 里取。
"""
from __future__ import annotations

import json
import re
from typing import Any, Tuple

from .base import Provider, ProviderError, http_json

_PLACEHOLDER = re.compile(r"\{(text|from|to)\}")


class CustomProvider(Provider):
    key = "custom"
    label = "自定义 HTTP 接口"
    detail = "填入任意翻译接口的地址、请求体模板与结果路径"
    requires_key = False
    max_chunk = 1500

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        c = (cfg or {}).get("custom") or {}
        if not str(c.get("url") or "").strip():
            return False, "未填写接口地址"
        return True, ""

    @staticmethod
    def _pick(data: Any, path: str) -> Any:
        cur = data
        for part in (path or "").split("."):
            if not part:
                continue
            if isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                    continue
                except (ValueError, IndexError):
                    return None
            if isinstance(cur, dict):
                if part not in cur:
                    return None
                cur = cur[part]
            else:
                return None
        return cur

    def translate_chunk(self, text: str, src: str, dst: str):
        c = self.cfg.get("custom") or {}
        url = str(c.get("url") or "").strip()
        method = str(c.get("method") or "POST").upper()
        body_tpl = str(c.get("body") or "").strip() or '{"text": "{text}"}'

        def sub(m):
            return {"text": text, "from": src, "to": dst}[m.group(1)]

        substituted = _PLACEHOLDER.sub(sub, body_tpl)
        try:
            payload = json.loads(substituted)
        except json.JSONDecodeError as e:
            raise ProviderError("请求体模板不是合法 JSON：%s" % e)

        try:
            headers = json.loads(str(c.get("headers") or "{}"))
        except json.JSONDecodeError:
            headers = {}
        if not isinstance(headers, dict):
            headers = {}

        data = http_json(url, method=method, payload=payload, headers=headers,
                         timeout=self.timeout)
        value = self._pick(data, str(c.get("result_path") or ""))
        if value is None:
            raise ProviderError("从响应里找不到结果路径「%s」，原始响应：%s"
                                % (c.get("result_path"), str(data)[:200]))
        if isinstance(value, list):
            value = "\n".join(str(v) for v in value)
        out = str(value)
        if not out.strip():
            raise ProviderError("自定义接口返回了空译文")
        return out, ""
