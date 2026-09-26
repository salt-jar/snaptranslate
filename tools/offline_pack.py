# -*- coding: utf-8 -*-
"""离线翻译语言包的命令行管理工具。

用法::

    python tools/offline_pack.py --available              # 列出可下载的语言包
    python tools/offline_pack.py --installed              # 列出已安装的
    python tools/offline_pack.py --download zh-en         # 下载中文→英文
    python tools/offline_pack.py --download zh-en,en-zh   # 双向一起下
    python tools/offline_pack.py --download zh-en en-zh   # 也可以空格分隔
    python tools/offline_pack.py --download-popular       # 下载中英 + 中日常用组合
    python tools/offline_pack.py --remove en-zh           # 删除
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

paths.bootstrap_import_path()

from app import offline  # noqa: E402

#: 常用语言对，--download-popular 会下载这些里索引中存在的
POPULAR = [
    ("zh", "en"), ("en", "zh"),
    ("zh", "ja"), ("ja", "zh"),
    ("zh", "ko"), ("ko", "zh"),
    ("zh", "fr"), ("fr", "zh"),
    ("zh", "de"), ("de", "zh"),
    ("zh", "ru"), ("ru", "zh"),
]


def parse_pair(text: str):
    for sep in ("-", "_", ":", "->", "→"):
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip().lower(), b.strip().lower()
    raise ValueError("看不懂的语言对：%s（示例：zh-en）" % text)


def human(mb: float) -> str:
    return "%.0f MB" % mb


def cmd_available(packs, args) -> int:
    packs = sorted(packs, key=lambda p: (p.from_code, p.to_code))
    if args.filter:
        kw = args.filter.lower()
        packs = [p for p in packs if kw in p.from_code or kw in p.to_code
                 or kw in p.from_name.lower() or kw in p.to_name.lower()]
    installed = offline.installed_pairs()
    print("可下载的语言包（共 %d 个）：" % len(packs))
    print("  %-14s %-24s %s" % ("代码", "语言对", "状态"))
    for p in packs:
        mark = "已安装" if p.pair in installed else ""
        print("  %-14s %-24s %s"
              % ("%s-%s" % (p.from_code, p.to_code),
                 "%s → %s" % (offline.lang_name(p.from_code),
                              offline.lang_name(p.to_code)), mark))
    print("\n下载：python tools/offline_pack.py --download zh-en")
    return 0


def cmd_installed(args) -> int:
    pairs = offline.installed_pairs()
    print("语言包目录：%s" % offline.models_root())
    if not pairs:
        print("  尚未安装任何语言包。")
        return 0
    total = 0.0
    for (a, b), path in sorted(pairs.items()):
        mb = offline.dir_size_mb(path)
        total += mb
        print("  %s → %s   %s" % (offline.lang_name(a), offline.lang_name(b), human(mb)))
    print("  合计 %.0f MB" % total)
    return 0


def _download(pairs, packs) -> int:
    index = {p.pair: p for p in packs}
    todo = []
    for a, b in pairs:
        p = index.get((a, b))
        if p is None:
            print("  [跳过] 索引里没有 %s → %s" % (offline.lang_name(a), offline.lang_name(b)))
            continue
        if p.pair in offline.installed_pairs():
            print("  [已有] %s → %s" % (offline.lang_name(a), offline.lang_name(b)))
            continue
        todo.append(p)

    if not todo:
        print("没有需要下载的语言包。")
        return 0

    failed = 0
    for i, p in enumerate(todo, 1):
        label = "%s → %s" % (offline.lang_name(p.from_code), offline.lang_name(p.to_code))
        print("\n[%d/%d] %s" % (i, len(todo), label))
        t0 = time.time()
        last = [-10]

        def progress(pct, note, last=last):
            if pct - last[0] >= 10 or pct >= 100:
                last[0] = pct
                print("   %3d%%  %s" % (pct, note), flush=True)

        try:
            path = offline.install_pack(p, progress=progress)
            print("   完成：%s（%.0f 秒，%.0f MB）"
                  % (path, time.time() - t0, offline.dir_size_mb(path)))
        except Exception as e:  # noqa: BLE001
            print("   失败：%s" % e)
            failed += 1
    return 1 if failed else 0


def cmd_download(args) -> int:
    pairs = [parse_pair(t) for t in args.download]
    packs = offline.fetch_index(force=args.refresh)
    print("索引：%d 个语言包" % len(packs))
    return _download(pairs, packs)


def cmd_download_popular(args) -> int:
    packs = offline.fetch_index(force=args.refresh)
    index = {p.pair: p for p in packs}
    pairs = [pr for pr in POPULAR if pr in index]
    print("索引中存在的常用组合：%d 个" % len(pairs))
    return _download(pairs, packs)


def cmd_remove(args) -> int:
    ok = 0
    for t in args.remove:
        a, b = parse_pair(t)
        if offline.remove_pack(a, b):
            print("  已删除 %s → %s" % (offline.lang_name(a), offline.lang_name(b)))
            ok += 1
        else:
            print("  未安装 %s → %s" % (offline.lang_name(a), offline.lang_name(b)))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="离线翻译语言包管理")
    ap.add_argument("--available", action="store_true", help="列出可下载的语言包")
    ap.add_argument("--installed", action="store_true", help="列出已安装的语言包")
    ap.add_argument("--download", nargs="+", metavar="PAIR",
                    help="下载语言包，如 zh-en；可多个（空格或逗号分隔）")
    ap.add_argument("--download-popular", action="store_true", help="下载常用语言对")
    ap.add_argument("--remove", nargs="+", metavar="PAIR", help="删除语言包")
    ap.add_argument("--filter", default="", help="配合 --available 过滤语言")
    ap.add_argument("--refresh", action="store_true", help="强制刷新索引（忽略缓存）")
    args = ap.parse_args()

    if args.download:
        # 支持逗号分隔
        flat = []
        for item in args.download:
            flat.extend(x for x in item.replace(",", " ").split() if x)
        args.download = flat

    from app.translate import local

    miss = local.missing_deps()
    if miss and (args.download or args.download_popular):
        print("缺少离线推理依赖：%s" % "、".join(miss))
        print("请先运行：python tools/install_deps.py")
        return 2

    if args.installed:
        return cmd_installed(args)
    if args.download:
        return cmd_download(args)
    if args.download_popular:
        return cmd_download_popular(args)
    if args.remove:
        return cmd_remove(args)

    packs = offline.fetch_index(force=args.refresh)
    return cmd_available(packs, args)


if __name__ == "__main__":
    sys.exit(main())
