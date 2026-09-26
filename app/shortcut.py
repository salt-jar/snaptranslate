# -*- coding: utf-8 -*-
"""创建桌面 / 开始菜单快捷方式。

优先用 PowerShell 的 WScript.Shell COM 组件（Windows 自带，无需任何依赖），
失败时退回 pywin32，再失败就在桌面写一个 .cmd。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from . import paths

_CREATE_NO_WINDOW = 0x08000000
SHORTCUT_NAME = "截译 截图翻译"


def desktop_dir() -> Path:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as k:
            raw, _ = winreg.QueryValueEx(k, "Desktop")
        return Path(os.path.expandvars(raw))
    except Exception:
        return Path.home() / "Desktop"


def start_menu_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return Path.home() / "Start Menu" / "Programs"


def launch_target() -> Tuple[str, str, str]:
    """返回 ``(可执行文件, 参数, 工作目录)``。"""
    app_dir = str(paths.app_dir())
    if paths.is_frozen():
        return sys.executable, "", app_dir
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")      # pythonw 启动不弹黑框
    target = str(pyw if pyw.exists() else exe)
    return target, '"%s"' % (Path(app_dir) / "main.py"), app_dir


def _powershell_create(lnk: Path, target: str, arguments: str, workdir: str,
                       icon: str, desc: str) -> Tuple[bool, str]:
    script = (
        "$ErrorActionPreference='Stop';"
        "$ws = New-Object -ComObject WScript.Shell;"
        "$sc = $ws.CreateShortcut({lnk});"
        "$sc.TargetPath = {target};"
        "$sc.Arguments = {args};"
        "$sc.WorkingDirectory = {wd};"
        "$sc.Description = {desc};"
        "{icon}"
        "$sc.Save();"
        "Write-Output 'OK'"
    ).format(
        lnk=_ps(lnk), target=_ps(target), args=_ps(arguments), wd=_ps(workdir),
        desc=_ps(desc),
        icon=("$sc.IconLocation = %s;" % _ps(icon)) if icon and Path(icon).exists() else "",
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, timeout=40, creationflags=_CREATE_NO_WINDOW,
        )
        out = (proc.stdout or b"").decode("utf-8", "replace")
        err = (proc.stderr or b"").decode("utf-8", "replace")
        if proc.returncode == 0 and "OK" in out:
            return True, ""
        return False, (err or out).strip()[:300]
    except Exception as e:  # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def _ps(value) -> str:
    """转成 PowerShell 单引号字符串（单引号本身翻倍转义）。"""
    return "'" + str(value).replace("'", "''") + "'"


def _pywin32_create(lnk: Path, target: str, arguments: str, workdir: str,
                    icon: str, desc: str) -> Tuple[bool, str]:
    try:
        import pythoncom  # type: ignore
        from win32com.shell import shell  # type: ignore
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    try:
        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink,
        )
        link.SetPath(target)
        if arguments:
            link.SetArguments(arguments)
        link.SetWorkingDirectory(workdir)
        if desc:
            link.SetDescription(desc)
        if icon and Path(icon).exists():
            link.SetIconLocation(str(icon), 0)
        persist = link.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Save(str(lnk), 1)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def create_shortcut(directory: Optional[Path] = None,
                    name: str = SHORTCUT_NAME) -> Tuple[bool, str]:
    """在指定目录（默认桌面）创建快捷方式，返回 ``(成功, 说明/错误)``。"""
    directory = Path(directory) if directory else desktop_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # noqa: BLE001
        return False, "无法访问目标目录 %s：%s" % (directory, e)

    target, arguments, workdir = launch_target()
    icon = str(paths.icon_path())
    desc = "截译 —— 截图即翻译（支持全局快捷键）"
    lnk = directory / ("%s.lnk" % name)

    ok, err = _powershell_create(lnk, target, arguments, workdir, icon, desc)
    if not ok:
        ok, err2 = _pywin32_create(lnk, target, arguments, workdir, icon, desc)
        if not ok:
            return _write_fallback_script(directory, name, target, arguments, workdir,
                                          err or err2)
    return True, str(lnk)


def _write_fallback_script(directory: Path, name: str, target: str, arguments: str,
                           workdir: str, why: str) -> Tuple[bool, str]:
    """连 COM 都用不了时，退化成 .cmd（双击同样能启动）。"""
    cmd = directory / ("%s.cmd" % name)
    try:
        cmd.write_text(
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "cd /d \"%s\"\r\n"
            "start \"\" \"%s\" %s\r\n" % (workdir, target, arguments),
            encoding="utf-8",
        )
    except Exception as e:  # noqa: BLE001
        return False, "创建快捷方式失败：%s；备用脚本也写入失败：%s" % (why, e)
    return True, "%s（快捷方式创建失败：%s，已改为生成启动脚本）" % (cmd, why)


def remove_shortcut(directory: Optional[Path] = None,
                    name: str = SHORTCUT_NAME) -> Tuple[bool, str]:
    directory = Path(directory) if directory else desktop_dir()
    removed = []
    for suffix in (".lnk", ".cmd"):
        p = directory / (name + suffix)
        if p.exists():
            try:
                p.unlink()
                removed.append(p.name)
            except Exception:
                pass
    if removed:
        return True, "已删除：" + "、".join(removed)
    return False, "桌面上没有找到快捷方式"


def shortcut_exists(directory: Optional[Path] = None,
                    name: str = SHORTCUT_NAME) -> bool:
    directory = Path(directory) if directory else desktop_dir()
    return (directory / (name + ".lnk")).exists() or (directory / (name + ".cmd")).exists()
