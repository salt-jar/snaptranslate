# -*- coding: utf-8 -*-
"""ctranslate2 的 PyInstaller 钩子。

**这个钩子里绝对不能 import ctranslate2（也不能 import sentencepiece）。**
PyInstaller 进程此时已经加载了 PyQt5，之后再导入这两个包会让子进程直接崩溃
（``SubprocessDiedError``，退出码 3221225477 = 0xC0000005 访问违例）。
所以全部改成按固定路径收集文件，不触碰包本身。

需要在本地解包 ctranslate2 的 56MB ``ctranslate2.dll`` 与 ``libiomp5md.dll``——
它们是运行时动态加载的，不显式收集的话打包版会在加载离线模型时报错。
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PKG = _ROOT / "vendor" / "ctranslate2"

datas = []
binaries = []
hiddenimports = []

if _PKG.is_dir():
    binaries += [(str(p), "ctranslate2") for p in sorted(_PKG.glob("*.dll"))]
    binaries += [(str(p), "ctranslate2") for p in sorted(_PKG.glob("*.pyd"))]
