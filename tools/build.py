# -*- coding: utf-8 -*-
"""打包成免安装的 exe（PyInstaller）。

用法::

    python tools/build.py              # 打包
    python tools/build.py --shortcut   # 打包后顺便把桌面快捷方式指向 exe
    python tools/build.py --clean      # 先清掉 build/ 与 dist/

产物在 ``dist/SnapTranslate/``，整个文件夹拷到别的电脑也能直接运行。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

SPEC = ROOT / "shotranslate.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def run(cmd, **kw) -> int:
    print("$ %s" % " ".join(str(c) for c in cmd))
    return subprocess.call([str(c) for c in cmd], cwd=str(ROOT), **kw)


def dir_size(path: Path) -> str:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return "%.1f MB" % (total / 1048576)


def main() -> int:
    ap = argparse.ArgumentParser(description="打包 截译 SnapTranslate")
    ap.add_argument("--clean", action="store_true", help="打包前清理 build/ 与 dist/")
    ap.add_argument("--shortcut", action="store_true", help="打包后创建指向 exe 的桌面快捷方式")
    ap.add_argument("--start-menu", action="store_true", help="打包后创建开始菜单快捷方式")
    args = ap.parse_args()

    print("=" * 70)
    print("  截译 SnapTranslate 打包")
    print("=" * 70)

    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("  [!!] 没有找到 PyInstaller。请先运行：")
        print("       python -m pip install pyinstaller")
        return 2

    if not SPEC.exists():
        print("  [!!] 找不到 %s" % SPEC)
        return 2

    if args.clean:
        for d in (DIST, BUILD):
            if d.exists():
                print("  清理 %s" % d)
                shutil.rmtree(d, ignore_errors=True)

    t0 = time.time()
    code = run([sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"])
    if code != 0:
        print("  [!!] 打包失败，退出码 %d" % code)
        return code

    out = DIST / "SnapTranslate"
    exe = out / "SnapTranslate.exe"
    print("\n" + "-" * 70)
    if not exe.exists():
        print("  [!!] 没有找到产物 %s" % exe)
        return 1
    print("  打包完成，耗时 %.0f 秒" % (time.time() - t0))
    print("  输出目录：%s" % out)
    print("  可执行文件：%s" % exe)
    print("  总体积：%s" % dir_size(out))
    print("  提示：把整个 SnapTranslate 文件夹拷走即可在别的电脑上免安装运行。")
    print("-" * 70)

    if args.shortcut or args.start_menu:
        from app import shortcut

        # 让快捷方式指向打包后的 exe
        shortcut.launch_target = lambda: (str(exe), "", str(out))  # type: ignore
        directory = shortcut.start_menu_dir() if args.start_menu else None
        ok, msg = shortcut.create_shortcut(directory)
        print(("  ✓ " if ok else "  ![ ] ") + msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
