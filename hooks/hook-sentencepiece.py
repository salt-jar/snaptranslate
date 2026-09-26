# -*- coding: utf-8 -*-
"""sentencepiece 的 PyInstaller 钩子。

**这个钩子里绝对不能 import sentencepiece。** PyInstaller 的默认流程会去
import 目标包来取 ``__file__``，而该进程已加载 PyQt5，此时导入 sentencepiece
会让子进程崩溃（0xC0000005 访问违例，见 hook-ctranslate2.py 的说明）。

这里按固定路径收集：
* ``package_data/*.bin`` —— 文本归一化表，缺了首次翻译就报错；
* ``*.pyd`` —— 原生扩展本体。
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PKG = _ROOT / "vendor" / "sentencepiece"

datas = []
binaries = []
hiddenimports = []

if _PKG.is_dir():
    if (_PKG / "package_data").is_dir():
        datas.append((str(_PKG / "package_data"), "sentencepiece/package_data"))
    binaries += [(str(p), "sentencepiece") for p in sorted(_PKG.glob("*.pyd"))]
