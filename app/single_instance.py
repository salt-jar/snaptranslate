# -*- coding: utf-8 -*-
"""单实例控制 + 命令行转发。

**为什么不用 QLocalServer / 命名管道**：命名管道在不少受限环境里会被拒绝
（实测某些沙箱 / 安全软件下 ``QLocalServer::listen`` 直接返回"拒绝访问"），
一旦失败就失去单实例保护，可以无限多开。这里改用**文件队列**：

* ``.ipc/instance.lock`` —— 记录主实例的 PID 与令牌；
* ``.ipc/queue/<时间戳>-<随机>.cmd`` —— 待处理命令，主实例轮询消费。

纯标准库实现、不依赖 Qt，所以可以在创建 ``QApplication`` **之前**就判断
"是否已有实例"，避免白启动一个完整的 GUI 进程。
"""
from __future__ import annotations

import ctypes
import json
import os
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, QTimer

from . import paths

_SYNCHRONIZE = 0x00100000
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_WAIT_TIMEOUT = 0x102


def pid_alive(pid: int) -> bool:
    """进程是否仍在运行。

    不能用 ``os.kill(pid, 0)``：在 Windows 上 ``os.kill`` 会直接调用
    ``TerminateProcess``，sig=0 会真的把对方杀掉。
    """
    if not pid or pid <= 0:
        return False
    try:
        kernel32 = ctypes.windll.kernel32
    except Exception:
        return False
    handle = kernel32.OpenProcess(
        _SYNCHRONIZE | _PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def _lock_path() -> Path:
    return paths.ipc_dir() / "instance.lock"


def _queue_dir() -> Path:
    return paths.ipc_dir() / "queue"


def find_running_pid() -> Optional[int]:
    """已有实例在运行则返回其 PID，否则 None。"""
    try:
        data = json.loads(_lock_path().read_text("utf-8"))
    except Exception:
        return None
    pid = int(data.get("pid") or 0)
    return pid if pid_alive(pid) else None


def forward_command(command: str) -> bool:
    """把命令投递给已在运行的实例。成功返回 True（调用方随后应直接退出）。"""
    if find_running_pid() is None:
        return False
    try:
        q = _queue_dir()
        q.mkdir(parents=True, exist_ok=True)
        name = "%d-%s.cmd" % (time.time_ns(), uuid.uuid4().hex[:8])
        tmp = q / (name + ".tmp")
        tmp.write_text(command, encoding="utf-8")
        tmp.replace(q / name)        # 原子改名，避免主实例读到半个文件
        return True
    except Exception:
        return False


class SingleInstance(QObject):
    """主实例持有它来消费命令队列。"""

    POLL_MS = 400

    def __init__(self, on_command: Callable[[str], None], parent=None):
        super().__init__(parent)
        self._on_command = on_command
        self._queue = _queue_dir()
        self._lock = _lock_path()
        self._timer: Optional[QTimer] = None
        self._seen: set = set()
        self._token = uuid.uuid4().hex

    def listen(self) -> str:
        """登记为当前主实例并开始轮询。返回后端描述文字。"""
        try:
            self._queue.mkdir(parents=True, exist_ok=True)
            self._lock.parent.mkdir(parents=True, exist_ok=True)
            self._lock.write_text(
                json.dumps({"pid": os.getpid(), "token": self._token,
                            "started": time.time()}, ensure_ascii=False),
                encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            return "文件锁不可用（%s），多开将不受限制" % e

        self._drain(dispatch=False)      # 丢弃上次异常退出遗留的旧命令
        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._drain)
        self._timer.start()
        return "文件队列 %s" % self._queue

    def _drain(self, dispatch: bool = True) -> None:
        try:
            files = sorted(self._queue.glob("*.cmd"))
        except Exception:
            return
        for f in files:
            if f.name in self._seen:
                continue
            self._seen.add(f.name)
            try:
                command = f.read_text(encoding="utf-8").strip()
            except Exception:
                command = ""
            try:
                f.unlink()
            except Exception:
                pass
            if dispatch and command:
                try:
                    self._on_command(command)
                except Exception:
                    pass

    def release(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        try:
            data = json.loads(self._lock.read_text("utf-8"))
            if data.get("token") == self._token:
                self._lock.unlink()
        except Exception:
            pass
        try:
            for f in self._queue.glob("*"):
                f.unlink()
        except Exception:
            pass
