# -*- coding: utf-8 -*-
"""全局快捷键。

两种后端：

* **native** —— Win32 ``RegisterHotKey``，注册成功后按键会被系统吞掉，
  不会同时传给当前窗口，是截图类工具最理想的方式。
* **listener** —— ``pynput`` 低级键盘钩子。原生注册失败时（被 QQ / 微信等占用）
  作为兜底，缺点是按键仍会传给前台窗口。

``mode='auto'`` 时优先原生，失败的动作自动退回钩子。
"""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal

# --------------------------------------------------------------------- Win32

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_NOREMOVE = 0x0000

ERROR_HOTKEY_ALREADY_REGISTERED = 1409

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT
]
user32.PeekMessageW.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

# --------------------------------------------------------------------- 按键表

_MOD_NAMES = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT, "shift": MOD_SHIFT,
    "win": MOD_WIN, "super": MOD_WIN, "cmd": MOD_WIN, "meta": MOD_WIN,
}

_NAMED_VK = {
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, "\\": 0xDC,
    ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
    "printscreen": 0x2C, "pause": 0x13, "capslock": 0x14,
}

_VK_NAMES = {v: k for k, v in _NAMED_VK.items()}

# 供设置界面使用
PRESET_HOTKEYS = [
    "Ctrl+Alt+Z", "Ctrl+Alt+X", "Ctrl+Alt+C", "Ctrl+Alt+A", "Ctrl+Alt+S",
    "Ctrl+Shift+A", "Ctrl+Shift+Z", "Ctrl+Shift+S", "Alt+Shift+A",
    "Alt+Q", "Alt+Z", "F4", "F6", "F8", "Ctrl+Alt+F4",
]


class HotkeyError(ValueError):
    pass


def parse_hotkey(text: str) -> Tuple[int, int, str]:
    """把 ``"Ctrl+Alt+Z"`` 解析为 ``(modifiers, vk, 标准写法)``。"""
    raw = (text or "").strip()
    if not raw:
        raise HotkeyError("快捷键为空")
    parts = [p.strip() for p in raw.replace("_", "+").split("+") if p.strip()]
    if not parts:
        raise HotkeyError("快捷键为空")

    mods = 0
    main: Optional[str] = None
    for p in parts:
        low = p.lower()
        if low in _MOD_NAMES:
            mods |= _MOD_NAMES[low]
        elif main is None:
            main = low
        else:
            raise HotkeyError("只能包含一个主键：%s" % raw)

    if main is None:
        raise HotkeyError("缺少主键：%s" % raw)

    if len(main) == 1 and (main.isalpha() or main.isdigit()):
        vk = ord(main.upper())
    elif main.startswith("f") and main[1:].isdigit() and 1 <= int(main[1:]) <= 24:
        vk = 0x70 + int(main[1:]) - 1
    elif main in _NAMED_VK:
        vk = _NAMED_VK[main]
    else:
        raise HotkeyError("不支持的按键：%s" % main)

    if mods == 0 and not (0x70 <= vk <= 0x87) and vk not in (0x2C, 0x13):
        raise HotkeyError("请至少使用一个修饰键（Ctrl / Alt / Shift / Win）")

    return mods, vk, format_hotkey(mods, vk)


def format_hotkey(mods: int, vk: int) -> str:
    out: List[str] = []
    if mods & MOD_CONTROL:
        out.append("Ctrl")
    if mods & MOD_ALT:
        out.append("Alt")
    if mods & MOD_SHIFT:
        out.append("Shift")
    if mods & MOD_WIN:
        out.append("Win")
    if 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
        out.append(chr(vk))
    elif 0x70 <= vk <= 0x87:
        out.append("F%d" % (vk - 0x70 + 1))
    else:
        name = _VK_NAMES.get(vk)
        out.append(name.upper() if name and len(name) == 1 else (name or "0x%02X" % vk).title())
    return "+".join(out)


def canonical(text: str) -> str:
    try:
        return parse_hotkey(text)[2]
    except HotkeyError:
        return (text or "").strip()


# --------------------------------------------------------------------- 后端


class _NativeBackend:
    """独立线程 + Win32 消息循环实现 RegisterHotKey。"""

    name = "native"

    def __init__(self, callback, on_error):
        self._callback = callback
        self._on_error = on_error
        self._bindings: Dict[int, str] = {}   # id -> action
        self._specs: List[Tuple[str, int, int]] = []  # (action, mods, vk)
        self._thread: Optional[threading.Thread] = None
        self._tid: Optional[int] = None
        self._ready = threading.Event()
        self._failed: Dict[str, str] = {}

    @property
    def registered(self) -> bool:
        """当前是否有至少一个快捷键由系统热键接管。"""
        return bool(self._bindings)

    def start(self, specs: List[Tuple[str, int, int]]) -> Dict[str, str]:
        self._specs = specs
        self._ready.clear()
        self._failed = {}
        self._thread = threading.Thread(target=self._run, name="hotkey-native", daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        return dict(self._failed)

    def _run(self) -> None:
        self._tid = int(kernel32.GetCurrentThreadId())
        # 强制创建线程消息队列，之后 PostThreadMessage 才能生效
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0x0400, 0x0400, PM_NOREMOVE)

        for idx, (action, mods, vk) in enumerate(self._specs, start=1):
            ok = user32.RegisterHotKey(None, idx, mods | MOD_NOREPEAT, vk)
            if ok:
                self._bindings[idx] = action
            else:
                err = ctypes.get_last_error()
                self._failed[action] = (
                    "已被其它程序占用" if err == ERROR_HOTKEY_ALREADY_REGISTERED
                    else "注册失败(错误码 %d)" % err
                )
        self._ready.set()

        if not self._bindings:
            return  # 全部失败，直接退出线程

        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):
                break
            if msg.message == WM_HOTKEY:
                action = self._bindings.get(int(msg.wParam))
                if action:
                    try:
                        self._callback(action)
                    except Exception:
                        pass

        for idx in list(self._bindings):
            user32.UnregisterHotKey(None, idx)
        self._bindings.clear()

    def stop(self) -> None:
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)
        self._thread = None
        self._tid = None


class _ListenerBackend:
    """pynput 低级钩子后端。"""

    name = "listener"

    def __init__(self, callback, on_error):
        self._callback = callback
        self._on_error = on_error
        self._listener = None
        self._pressed: set = set()
        self._fired: set = set()
        self._targets: Dict[frozenset, str] = {}

    @staticmethod
    def available() -> bool:
        try:
            import pynput  # noqa: F401

            return True
        except Exception:
            return False

    def start(self, specs: List[Tuple[str, int, int]]) -> Dict[str, str]:
        try:
            from pynput import keyboard
        except Exception as e:  # noqa: BLE001
            return {a: "pynput 不可用：%s" % e for a, _, _ in specs}

        self._targets.clear()
        for action, mods, vk in specs:
            keys = set()
            if mods & MOD_CONTROL:
                keys.add("ctrl")
            if mods & MOD_ALT:
                keys.add("alt")
            if mods & MOD_SHIFT:
                keys.add("shift")
            if mods & MOD_WIN:
                keys.add("win")
            if 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
                keys.add(chr(vk).lower())
            elif 0x70 <= vk <= 0x87:
                keys.add("f%d" % (vk - 0x70 + 1))
            else:
                nm = _VK_NAMES.get(vk)
                if nm:
                    keys.add(nm)
            if keys:
                self._targets[frozenset(keys)] = action

        self._keyboard = keyboard
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()
        return {}

    @staticmethod
    def _normalize(key) -> Optional[str]:
        try:
            from pynput import keyboard

            if isinstance(key, keyboard.Key):
                name = key.name  # ctrl_l / alt_gr / f4 / space ...
                if name.startswith("ctrl"):
                    return "ctrl"
                if name.startswith("alt"):
                    return "alt"
                if name.startswith("shift"):
                    return "shift"
                if name.startswith("cmd"):
                    return "win"
                return name
            ch = getattr(key, "char", None)
            if ch:
                return ch.lower()
        except Exception:
            pass
        return None

    def _on_press(self, key) -> None:
        k = self._normalize(key)
        if not k:
            return
        self._pressed.add(k)
        frozen = frozenset(self._pressed)
        for keys, action in self._targets.items():
            if keys <= frozen and action not in self._fired:
                self._fired.add(action)
                try:
                    self._callback(action)
                except Exception:
                    pass

    def _on_release(self, key) -> None:
        k = self._normalize(key)
        if not k:
            return
        self._pressed.discard(k)
        for keys, action in list(self._targets.items()):
            if not keys <= self._pressed:
                self._fired.discard(action)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._pressed.clear()
        self._fired.clear()


# --------------------------------------------------------------------- 管理器


class HotkeyManager(QObject):
    """对外统一接口。``bindings`` 为 ``{动作名: "Ctrl+Alt+Z"}``。"""

    triggered = pyqtSignal(str)          # 动作名
    conflicts = pyqtSignal(dict)         # {动作名: 失败原因}
    backend_changed = pyqtSignal(str)    # 描述文字

    def __init__(self, parent=None):
        super().__init__(parent)
        self._native = _NativeBackend(self._emit, None)
        self._listener: Optional[_ListenerBackend] = None
        self._active_backend = ""
        self._bindings: Dict[str, str] = {}

    # ---------------------------------------------------------------- 内部

    def _emit(self, action: str) -> None:
        self.triggered.emit(action)

    def _stop_all(self) -> None:
        self._native.stop()
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._active_backend = ""

    def _start(self, specs, use_native: bool, use_listener: bool):
        """返回 (失败字典, 后端名)。"""
        failed: Dict[str, str] = {}
        backend = ""
        remaining = list(specs)

        if use_native:
            failed = self._native.start(remaining)
            if self._native.registered:
                backend = "native"
                remaining = [s for s in remaining if s[0] in failed]
            else:
                remaining = list(specs)   # 原生全败，全部交给钩子

        if remaining and use_listener:
            if _ListenerBackend.available():
                lb = _ListenerBackend(self._emit, None)
                lfail = lb.start(remaining)
                if lb._listener is not None:
                    self._listener = lb
                    backend = (backend + "+listener") if backend else "listener"
                    for a in list(failed):
                        if a not in lfail:
                            failed.pop(a, None)   # 钩子接住了，不再算失败
                failed.update(lfail)
            else:
                for a, _, _ in remaining:
                    if a not in failed:
                        failed[a] = "未被系统接受，且未安装 pynput 兜底"

        return failed, backend

    # ---------------------------------------------------------------- 公开

    def apply(self, bindings: Dict[str, str], mode: str = "auto") -> Dict[str, str]:
        """应用一组快捷键，返回失败明细 ``{动作: 原因}``。"""
        self._stop_all()
        self._bindings = dict(bindings or {})

        specs: List[Tuple[str, int, int]] = []
        failed: Dict[str, str] = {}
        for action, text in self._bindings.items():
            if not text:
                continue
            try:
                mods, vk, _ = parse_hotkey(text)
            except HotkeyError as e:
                failed[action] = str(e)
                continue
            specs.append((action, mods, vk))

        if not specs:
            self._active_backend = "off"
            self.backend_changed.emit("未启用")
            if failed:
                self.conflicts.emit(failed)
            return failed

        use_native = mode in ("auto", "native")
        use_listener = mode in ("auto", "listener")
        failed2, backend = self._start(specs, use_native, use_listener)
        failed.update(failed2)

        self._active_backend = backend or "none"
        desc = {
            "native": "系统热键（推荐）",
            "listener": "键盘钩子模式（按键会同时传给当前窗口）",
            "native+listener": "系统热键 + 钩子混合",
            "none": "注册失败",
            "off": "未启用",
        }.get(self._active_backend, self._active_backend)
        self.backend_changed.emit(desc)
        if failed:
            self.conflicts.emit(dict(failed))
        return failed

    def stop(self) -> None:
        self._stop_all()
