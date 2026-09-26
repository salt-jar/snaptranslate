# -*- coding: utf-8 -*-
"""PyInstaller 隔离子进程的预加载钩子。

**为什么需要这个文件**

PyInstaller 会启动一个**长期复用**的隔离子进程来做模块内省。那个子进程在分析
PyQt5 相关 hook 时先加载了 Qt；而一旦 Qt 已经加载，之后再 ``import sentencepiece``
会让子进程直接崩溃：

    SubprocessDiedError: Child process died calling import_library() with args=('sentencepiece',)
    Its exit code was 3221225477   # 0xC0000005 访问违例

实测的导入顺序规律：

    PyQt5.QtCore -> sentencepiece             崩溃
    sentencepiece -> PyQt5.QtCore             OK
    ctranslate2 -> PyQt5.QtCore -> sentencepiece   OK   ← 靠这一条

也就是说，只要 ``ctranslate2`` 先于 Qt 被导入，后面的 sentencepiece 就安全了。
这个文件会被 Python 启动时自动 import（sitecustomize 机制），
从而保证 PyInstaller 的每个子进程都先加载 ctranslate2。

用法见 tools/build.py：打包时把本目录加进 PYTHONPATH。
"""
try:
    import ctranslate2  # noqa: F401
except Exception:
    # 没装离线翻译依赖时忽略即可，不影响 OCR 部分的打包
    pass
