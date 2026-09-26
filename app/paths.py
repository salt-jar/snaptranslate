# -*- coding: utf-8 -*-
"""路径、运行环境与自启动注册。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "截译"
APP_ID = "SnapTranslate"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------- 运行环境


def is_frozen() -> bool:
    """是否由 PyInstaller 打包后运行。"""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """程序所在目录：源码运行=项目根目录，打包后=exe 所在目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """只读资源目录（打包后指向 _MEIPASS 解包目录）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", str(app_dir())))
    return app_dir()


def vendor_dir() -> Path:
    """工作区内的第三方依赖目录（pip install --target vendor）。"""
    return app_dir() / "vendor"


def bootstrap_import_path() -> bool:
    """把 vendor/ 加入 sys.path，使程序无需安装依赖即可运行。

    返回 vendor 目录是否存在。
    """
    if is_frozen():
        return False
    vd = vendor_dir()
    if vd.is_dir():
        p = str(vd)
        if p not in sys.path:
            sys.path.insert(0, p)
        # 让 shapely / pyclipper 等带 DLL 的包能找到自己的动态库
        try:
            os.add_dll_directory(p)
        except (AttributeError, OSError, FileNotFoundError):
            pass
        return True
    return False


def icon_path() -> Path:
    for name in ("icon.ico", "icon.png"):
        p = resource_dir() / "resources" / name
        if p.exists():
            return p
    return resource_dir() / "resources" / "icon.ico"


# --------------------------------------------------------------------------- 配置目录


def _writable(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("1", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def config_dir() -> Path:
    """优先程序目录（绿色便携），不可写时退回 %APPDATA%。"""
    portable = app_dir()
    if _writable(portable):
        return portable
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_ID


def config_path() -> Path:
    return config_dir() / "config.json"


def log_path() -> Path:
    return config_dir() / "snaptranslate.log"


def cache_dir() -> Path:
    d = config_dir() / ".cache"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def ipc_dir() -> Path:
    """单实例通信目录（详见 app/single_instance.py）。"""
    d = config_dir() / ".ipc"
    try:
        (d / "queue").mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


# --------------------------------------------------------------------------- 启动项

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command() -> str:
    if is_frozen():
        return f'"{sys.executable}"'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    return f'"{exe}" "{app_dir() / "main.py"}"'


def is_autostart_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, APP_ID)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart(enable: bool) -> bool:
    """写入/删除 HKCU Run 启动项。"""
    try:
        import winreg

        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, APP_ID, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_ID)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False
