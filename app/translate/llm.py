# -*- coding: utf-8 -*-
"""AI 大模型翻译（OpenAI 兼容接口）。

支持 DeepSeek、Kimi、通义千问、智谱 GLM、硅基流动、OpenAI 等任何兼容
``/chat/completions`` 的服务。填写 Key 后翻译质量明显优于免费引擎，
而且能很好地保留原文格式与专有名词。
"""
from __future__ import annotations

import re
from typing import Tuple

from ..langs import to_llm_name
from .base import Provider, ProviderError, http_json

_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_PREFIX = re.compile(r"^\s*(译文|翻译|translation|translated text)\s*[:：]\s*", re.I)
_QUOTES = "\"'“”‘’「」『』"


def normalize_base_url(url: str) -> str:
    """把用户填的各种写法统一成 ``.../chat/completions``。"""
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    if u.endswith("/chat/completions"):
        return u
    return u + "/chat/completions"


class LlmProvider(Provider):
    key = "llm"
    label = "AI 大模型翻译（需 Key）"
    detail = "DeepSeek / Kimi / 通义 / 智谱 / OpenAI 等，质量最好且支持任意语种"
    requires_key = True
    max_chunk = 2400

    @classmethod
    def available(cls, cfg: dict) -> Tuple[bool, str]:
        c = (cfg or {}).get("llm") or {}
        if not str(c.get("base_url") or "").strip():
            return False, "未填写接口地址（Base URL）"
        if not str(c.get("api_key") or "").strip():
            return False, "未填写 API Key"
        return True, ""

    def translate_chunk(self, text: str, src: str, dst: str):
        c = self.cfg.get("llm") or {}
        url = normalize_base_url(str(c.get("base_url") or ""))
        key = str(c.get("api_key") or "").strip()
        model = str(c.get("model") or "").strip()
        if not url or not key:
            raise ProviderError("大模型翻译未配置完整（需要接口地址与 API Key）")

        target_name = to_llm_name(dst)
        template = str(c.get("prompt") or "").strip() or (
            "你是一个专业翻译引擎。把用户给出的文本翻译成{target}。"
            "只输出译文本身，不要解释、不要引号，保持原文换行与格式。"
        )
        system = template.replace("{target}", target_name).replace("{to}", target_name)
        if src and src != "auto":
            system += "\n原文语言是：%s。" % to_llm_name(src)

        payload = {
            "model": model or "deepseek-chat",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "temperature": float(c.get("temperature", 0.2) or 0.2),
            "stream": False,
        }
        data = http_json(url, method="POST", payload=payload, timeout=max(self.timeout, 30),
                         headers={"Authorization": "Bearer %s" % key})

        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ProviderError("大模型接口报错：%s" % str(msg)[:200])

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("大模型返回格式异常：%s" % str(data)[:200])

        return self._clean(str(content))

    @staticmethod
    def _clean(text: str) -> str:
        out = text.strip()
        out = _FENCE.sub("", out).strip()
        out = _PREFIX.sub("", out)
        if len(out) >= 2 and out[0] in _QUOTES and out[-1] in _QUOTES:
            out = out[1:-1].strip()
        return out

    def translate(self, text: str, src: str, dst: str, progress=None):
        """大模型不分段（上下文更完整），一次调用即可。"""
        text = (text or "").strip()
        if not text:
            return "", ""
        if progress:
            progress(0, 1)
        return self.translate_chunk(text, src, dst)
