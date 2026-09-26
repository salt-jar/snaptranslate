# -*- coding: utf-8 -*-
"""启动阶段的面包屑日志。

用于排查「程序启动就崩、连正常日志都没来得及写」这类问题——
正常的 ``snaptranslate.log`` 是在 ``main()`` 里才建立的，如果崩溃发生在
那之前（比如某个原生库在导入时直接把进程干掉），就什么线索都没有。

这里最早在 ``main.py`` 的第一行就开始记录，每条一行，写到程序目录下的
``startup.log``。启动正常时这个文件只有寥寥几行，属于无害的诊断信息。
"""
from __future__ import annotations

import time
from pathlib import Path

_path: Path | None = None


def set_path(p) -> None:
    global _path
    try:
        _path = Path(p)
    except Exception:
        _path = None


def log(msg: str) -> None:
    """追加一行带时间戳的记录；失败时静默（诊断代码不能影响主流程）。"""
    if _path is None:
        return
    try:
        with open(_path, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def reset() -> None:
    """每次启动清空，避免文件无限增长。"""
    if _path is None:
        return
    try:
        with open(_path, "w", encoding="utf-8") as fh:
            fh.write("%s  ---- 启动 ----\n" % time.strftime("%H:%M:%S"))
    except Exception:
        pass
