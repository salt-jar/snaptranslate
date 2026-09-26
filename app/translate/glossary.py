# -*- coding: utf-8 -*-
"""译前保护：把不该被翻译的片段换成占位符，译完再还原。

为什么需要
----------
机器翻译会把代码标识符、文件名、版本号当成普通词来翻译，实测：

* ``config.json``  → ``config。json``（句点被换成全角，文件路径直接失效）
* ``PP-OCRv4``     → ``pp - ocv4``（模型名被拆开）
* ``ONNX Runtime`` → ``ONNX运行时``
* ``quantization`` → ``四进制``（离线引擎，词义选错）

对技术类截图来说这一类错误比"译得不够优雅"更致命，所以译前先替换成占位符、
译后原样换回来。

占位符选型
----------
实测 ``[[1]]``、``{1}``、``<1>``、``__1__``、``##1##`` 都能原样穿过有道与
Yandex，不会被改写、不会被翻译、也不会被拆开。这里用 ``[[n]]``：可读性好，
且几乎不可能与正文冲突。还原时用容错正则，允许引擎插入空格。

用户术语表
----------
除了自动识别，还支持用户自定义术语（``GPU=GPU``、``量化=quantization``）。
实现方式一致：把源术语换成占位符，还原时填**用户指定的译法**，
这样引擎既不会翻错，也不会把术语拆开。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

#: 占位符外形。``{12}``
#:
#: 格式是实测选出来的。最初的 ``[[n]]`` 被证明不可靠：有道在**独立成行**时原样放行，
#: 一旦嵌在句子里就会把它包成 ``[b[n]]``（b 是它的加粗标记），
#: 还原正则匹配不上，占位符直接泄漏到译文里。
#: 在出问题的那句话上反复测，``{n}`` 是唯一稳定存活的写法。
_PH = "{%d}"

#: 还原用。要容忍几种已知的引擎改写：
#:   1. ``{0}``        正常形态，可能被插空格
#:   2. ``[[0]]``      历史格式，保持兼容
#:   3. ``[b[0]]``     有道把 ``[[0]]`` 加粗后的样子
#:   4. ``[[0]``       被截断掉一个右括号
_RESTORE_RE = re.compile(
    r"\{\s*(\d+)\s*\}"                    # {0}
    r"|\[\s*\[\s*(\d+)\s*\]\s*\]"         # [[0]]
    r"|\[\s*b\s*\[\s*(\d+)\s*\]\s*\]"     # [b[0]]  ← 有道
    r"|\[\s*\[\s*(\d+)\s*\]"              # [[0]    ← 被截断
)

#: 清理残留：引擎可能把占位符拆碎，留下 ``[[0]``、``[b[``、``{0`` 这类碎片。
#: 宁可清掉也不能让它们出现在最终译文里。
#:
#: 两个必须守住的边界：
#: * **不能删完整的 ``{n}``** —— 它可能是刚刚还原回来的**内容**
#:   （源文本里本来就写着 ``{0}`` 的格式串），删了就丢东西；
#:   所以只清理"后面没有右花括号"的截断形态。
#: * 只匹配双中括号或花括号数字，免得误删译文里正常的「（1）」。
_LEFTOVER_RE = re.compile(
    r"\[\s*b?\s*\[\s*\d*\s*\]?\s*\]?"      # [[... / [b[... / [[0
    r"|\{\s*\d+\s*(?!\})"                  # 被截断的 {0（后面没有 }）
    r"|\{\s*\}"                            # 空花括号
)

#: 自动保护规则。顺序有讲究：
#: * 花括号表达式必须放**第一个**——占位符本身就是 ``{n}`` 的形状，
#:   如果它排在后面，会把自己刚生成的占位符再遮一遍（踩过这个坑）；
#: * URL / 路径这类"长且确定"的紧随其后，免得被后面的通用规则拆碎。
_AUTO_PATTERNS: List[re.Pattern] = [
    # 花括号表达式。必须保护源文本里本来就有的 `{0}`——否则它会和我们的
    # 占位符撞车，还原时被替换成别的词。
    re.compile(r"\{[^{}\n]{0,40}\}"),
    re.compile(r"https?://[^\s<>\"'）)】\]]+"),                 # URL
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),                  # 邮箱
    re.compile(                                                 # 带扩展名的文件名
        r"(?:[\w\u4e00-\u9fff./\\~-]*[/\\])?"                   # 可选路径前缀
        r"[\w\u4e00-\u9fff~-]+\."
        r"(?:json|ya?ml|py|pyi|js|mjs|cjs|ts|tsx|jsx|md|rst|txt|exe|dll|so|ini"
        r"|toml|cfg|conf|config|log|csv|tsv|xml|html?|css|scss|sh|bash|bat|cmd"
        r"|ps1|zip|tar|gz|bz2|xz|whl|onnx|pt|pth|db|sqlite|sql|lock|env|pem|key"
        r"|crt|ico|png|jpe?g|gif|svg|mp4|mp3|wav|pdf|docx?|xlsx?|pptx?)\b",
        re.IGNORECASE),
    re.compile(r"\bv?\d+\.\d+(?:\.\d+)*(?:[-+][\w.]+)?\b"),      # 版本号 1.2.3 / v1.0
    # 连字符型号：PP-OCRv4 / Python-3.13。
    # 要求破折号后面**含数字**，否则会把 well-known、up-to-date 这类
    # 普通复合词也保护起来，反而让它们得不到翻译。
    # 也不能只写成 -\d，那样 PP-OCRv4 只会匹配到后半截「OCRv4」，
    # 前面的 PP- 仍会被引擎翻掉。
    re.compile(r"\b[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9]*\d[\w.]*\b"),
    re.compile(r"\b[A-Za-z]{2,}\d[\w.-]*\b"),                   # OCRv4 / INT8 / UTF8
    re.compile(r"\b[A-Za-z][a-z0-9]*(?:[A-Z][a-z0-9]+)+\b"),    # CamelCase 标识符
    re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"),           # snake_case
    re.compile(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*\b"),              # module.attr
    re.compile(r"\b[A-Za-z_]\w*\(\s*\)"),                       # 函数调用
    re.compile(r"\b[A-Z]{3,}\b"),                               # 全大写缩写 OCR/GPU/ONNX
    re.compile(                                                 # 快捷键
        r"\b(?:Ctrl|Alt|Shift|Win|Cmd|Meta|Fn)"
        r"(?:\s*\+\s*(?:Ctrl|Alt|Shift|Win|Cmd|Meta|F\d{1,2}|[A-Z0-9]))+\b",
        re.IGNORECASE),
    re.compile(r"\$\{[^}]+\}|\{\{[^}]+\}\}|%[sd]\b"),           # 模板变量
]

#: 太短就不保护（一个字的大写字母、纯数字等本来就不会被乱翻）
_MIN_LEN = 2


class Glossary:
    """一次翻译所需的替换/还原上下文。"""

    def __init__(self, user_terms=None):
        # 用户术语：源 -> 期望译法。值为空表示"保持原样"。
        # 允许直接传配置里的原始值（列表 / 多行文本 / 字典），内部统一解析。
        if user_terms and not isinstance(user_terms, dict):
            user_terms = self.parse_terms(user_terms)
        self.user_terms: Dict[str, str] = {}
        for src, dst in (user_terms or {}).items():
            s = (src or "").strip()
            if s:
                self.user_terms[s] = (dst or "").strip() or s

    # ---------------------------------------------------------------- 保护

    def protect(self, text: str) -> Tuple[str, Dict[str, str]]:
        """返回 ``(替换后的文本, 槽位映射)``。"""
        slots: Dict[str, str] = {}
        out = text or ""

        # 1) 用户术语优先（长词优先，避免短词把长词切碎）
        for term in sorted(self.user_terms, key=len, reverse=True):
            if term and term in out:
                out = out.replace(term, self._slot(slots, self.user_terms[term]))

        # 2) 自动保护
        for pattern in _AUTO_PATTERNS:
            out = pattern.sub(lambda m: self._slot(slots, m.group(0)), out)

        return out, slots

    @staticmethod
    def _slot(slots: Dict[str, str], value: str) -> str:
        if len(value) < _MIN_LEN:
            return value
        # 防重入：如果这个串**已经是本轮的占位符**，就原样放行，不能再遮一层。
        # 否则 `{0}` 会被遮成 `{1}`，还原时报"槽位丢失"、内容也跟着丢。
        #
        # 注意判据必须是「已在 slots 里」，不能只看形状：源文本自带的 `{0}`
        # 形状一样，但它是**内容**，需要正常分配一个槽位，
        # 否则会和真占位符撞车。
        if value in slots:
            return value
        key = _PH % len(slots)
        slots[key] = value
        return key

    # ---------------------------------------------------------------- 还原

    @staticmethod
    def restore(text: str, slots: Dict[str, str]) -> Tuple[str, List[str]]:
        """把占位符换回原样。

        返回 ``(还原后的文本, 丢失的槽位列表)``。

        引擎偶尔会改写甚至吃掉占位符，所以这里做三层兜底：
        兼容已知变形 → 只替换确实存在的槽位（避免误伤译文里原本的括号数字）
        → 清掉残留碎片。丢失的槽位会回报给调用方，便于界面提示。
        """
        text = text or ""
        if not slots:
            return text, []

        hit: set = set()

        def sub(m: "re.Match") -> str:
            raw = next((g for g in m.groups() if g is not None), None)
            if raw is None:
                return m.group(0)
            key = _PH % int(raw)
            if key not in slots:
                # 不是我们的占位符——很可能是译文里本来就有的括号数字，别动它
                return m.group(0)
            hit.add(key)
            return slots[key]

        out = _RESTORE_RE.sub(sub, text)

        lost = [k for k in slots if k not in hit]

        # 清掉被拆碎的残骸（只处理"含空括号/孤立数字括号"这种明显不正常的形态）
        out = _LEFTOVER_RE.sub("", out)
        # 收拾因为删掉占位符而多出来的空格
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"[ \t]+([，。、；：！？）】」』,.!?;:)])", r"\1", out)
        return out.strip(), lost

    # ---------------------------------------------------------------- 便捷

    @classmethod
    def parse_terms(cls, raw) -> Dict[str, str]:
        """把配置里的术语表解析成字典。

        支持几种写法：``["GPU=GPU", "量化=quantization"]``（列表），
        ``{"GPU": "GPU"}``（字典），或者一整段多行文本。
        """
        terms: Dict[str, str] = {}
        if not raw:
            return terms
        if isinstance(raw, dict):
            for k, v in raw.items():
                terms[str(k).strip()] = str(v or "").strip()
            return terms
        items = raw if isinstance(raw, (list, tuple)) else str(raw).splitlines()
        for item in items:
            line = str(item).strip()
            if not line or line.startswith("#"):
                continue
            for sep in ("=>", "=", "\t", "→"):
                if sep in line:
                    k, _, v = line.partition(sep)
                    k, v = k.strip(), v.strip()
                    if k:
                        terms[k] = v
                    break
            else:
                terms[line] = line      # 只写一个词 = 保持原样
        return terms


def protect(text: str, user_terms: Optional[Dict[str, str]] = None):
    """``Glossary.protect`` 的函数式入口。"""
    return Glossary(user_terms).protect(text)
