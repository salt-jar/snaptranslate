# -*- coding: utf-8 -*-
"""命令行创建 / 删除桌面快捷方式。

用法::

    python tools/make_shortcut.py                # 创建到桌面
    python tools/make_shortcut.py --start-menu   # 创建到开始菜单
    python tools/make_shortcut.py --remove       # 删除桌面上的快捷方式
    python tools/make_shortcut.py --check        # 只检查是否已存在
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

from app import shortcut  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="创建截译的桌面快捷方式")
    ap.add_argument("--start-menu", action="store_true", help="创建到开始菜单")
    ap.add_argument("--remove", action="store_true", help="删除快捷方式")
    ap.add_argument("--check", action="store_true", help="只检查是否已存在")
    ap.add_argument("--name", default=shortcut.SHORTCUT_NAME, help="快捷方式名称")
    args = ap.parse_args()

    directory = shortcut.start_menu_dir() if args.start_menu else None
    where = "开始菜单" if args.start_menu else "桌面"
    target_dir = Path(directory) if directory else shortcut.desktop_dir()

    print("目标位置：%s" % target_dir)

    if args.check:
        exists = shortcut.shortcut_exists(target_dir, args.name)
        print("快捷方式%s存在" % ("已" if exists else "不"))
        return 0 if exists else 1

    if args.remove:
        ok, msg = shortcut.remove_shortcut(target_dir, args.name)
        print(("✓ " if ok else "✗ ") + msg)
        return 0 if ok else 1

    target, arguments, workdir = shortcut.launch_target()
    print("启动命令：%s %s" % (target, arguments))
    ok, msg = shortcut.create_shortcut(target_dir, args.name)
    print(("✓ 已创建：" if ok else "✗ 创建失败：") + msg)
    if ok:
        print("\n现在可以双击%s上的「%s」启动程序。" % (where, args.name))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
