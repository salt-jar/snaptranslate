# -*- coding: utf-8 -*-
"""离线语言包管理界面（iOS 风格列表）。

功能：获取语言包列表（多镜像）、按语言筛选、查看体积、下载 / 删除。
下载在后台线程里跑，界面不会卡；尺寸用后台 HEAD 请求补齐并缓存。
后台线程只发信号，所有界面更新都回到主线程。
"""
from __future__ import annotations

import json
import threading
import urllib.request
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from . import offline, paths, theme
from .widgets import FramelessDialog

_COL_PAIR, _COL_SIZE, _COL_STATE = 0, 1, 2


class OfflinePackDialog(FramelessDialog):
    changed = pyqtSignal()

    status_text = pyqtSignal(str)
    index_ready = pyqtSignal(object)
    index_failed = pyqtSignal(str)
    sizes_ready = pyqtSignal(object)
    progress_value = pyqtSignal(int, str)
    download_done = pyqtSignal()

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("离线语言包管理")
        self.setWindowIcon(QIcon(str(paths.icon_path())))
        self.set_title("离线语言包", "下载一次，之后翻译全程离线")
        self.resize(880, 690)
        self.setMinimumSize(720, 560)

        self._packs: List[offline.PackInfo] = []
        self._installed: Dict[Tuple[str, str], "object"] = {}
        self._sizes: Dict[str, float] = self._load_size_cache()
        self._busy = False
        self._cancel = False
        self._stop = threading.Event()

        self._build()
        self._wire_signals()
        self._refresh_installed()
        self._load_index()

    def _wire_signals(self) -> None:
        self.status_text.connect(self._set_status)
        self.index_ready.connect(self._on_index_ready)
        self.index_failed.connect(self._on_index_failed)
        self.sizes_ready.connect(self._on_sizes_ready)
        self.progress_value.connect(self._on_progress)
        self.download_done.connect(self._on_download_done)

    # ---------------------------------------------------------------- 构建

    def _build(self) -> None:
        root = self.body_layout
        root.setSpacing(12)

        tip = QLabel(
            "下载后翻译完全在本机完成，<b>文本不会离开你的电脑，也不会产生任何网络请求</b>。"
            "语言包保存在 <code>%s</code>。"
            % offline.models_root()
        )
        tip.setWordWrap(True)
        tip.setProperty("role", "hint")
        root.addWidget(tip)

        # ---- 筛选行 ----
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.cmb_lang = QComboBox()
        self.cmb_lang.setMinimumWidth(170)
        self.cmb_lang.setMaximumWidth(240)
        self.cmb_lang.currentIndexChanged.connect(self._populate)
        bar.addWidget(self.cmb_lang)

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("搜索语言…")
        self.ed_search.textChanged.connect(self._populate)
        bar.addWidget(self.ed_search, 1)

        self.btn_reload = QPushButton("刷新列表")
        self.btn_reload.clicked.connect(lambda: self._load_index(force=True))
        bar.addWidget(self.btn_reload)
        root.addLayout(bar)

        # ---- 表格 ----
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["语言对", "体积", "状态"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().setFixedHeight(38)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(_COL_PAIR, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            _COL_SIZE, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            _COL_STATE, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        root.addWidget(self.table, 1)

        # ---- 进度 ----
        self.bar_progress = QProgressBar()
        self.bar_progress.setRange(0, 100)
        self.bar_progress.setValue(0)
        self.bar_progress.setTextVisible(False)
        self.bar_progress.setVisible(False)
        root.addWidget(self.bar_progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("StatusLabel")
        root.addWidget(self.lbl_status)

        # ---- 按钮 ----
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_download = QPushButton("下载选中")
        self.btn_download.setProperty("accent", True)
        self.btn_download.clicked.connect(self._download_selected)
        btns.addWidget(self.btn_download)

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.setProperty("danger", True)
        self.btn_delete.clicked.connect(self._delete_selected)
        btns.addWidget(self.btn_delete)

        self.btn_open = QPushButton("打开目录")
        self.btn_open.clicked.connect(self._open_dir)
        btns.addWidget(self.btn_open)

        btns.addStretch(1)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        root.addLayout(btns)

        self._update_buttons()

    # ---------------------------------------------------------------- 数据

    def _refresh_installed(self) -> None:
        self._installed = offline.installed_pairs()

    def _set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    def _load_index(self, force: bool = False) -> None:
        if self._busy:
            return
        self._busy = True
        self.btn_reload.setEnabled(False)
        self.lbl_status.setText("正在获取语言包列表…")
        self._cancel = False
        stop = self._stop

        def work():
            try:
                packs = offline.fetch_index(force=force)
            except Exception as e:  # noqa: BLE001
                if not stop.is_set():
                    self.index_failed.emit(str(e))
                return
            if not stop.is_set():
                self.index_ready.emit(packs)

        threading.Thread(target=work, daemon=True).start()

    def _on_index_ready(self, packs) -> None:
        self._busy = False
        self.btn_reload.setEnabled(True)
        self._packs = list(packs)
        self._rebuild_lang_filter()
        self._populate()
        self._update_buttons()
        self.lbl_status.setText("共 %d 个语言包，可下载" % len(self._packs))
        threading.Thread(target=self._fetch_sizes, args=(list(self._packs),),
                         daemon=True).start()

    def _on_index_failed(self, message: str) -> None:
        self._busy = False
        self.btn_reload.setEnabled(True)
        self.lbl_status.setText("获取失败：%s" % message)

    def _rebuild_lang_filter(self) -> None:
        langs = offline.available_languages(self._packs)
        self.cmb_lang.blockSignals(True)
        self.cmb_lang.clear()
        self.cmb_lang.addItem("全部语言", "")
        for code in langs:
            self.cmb_lang.addItem("%s（%s）" % (offline.lang_name(code), code), code)
        idx = self.cmb_lang.findData("zh")
        self.cmb_lang.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_lang.blockSignals(False)

    def _populate(self) -> None:
        lang = self.cmb_lang.currentData() or ""
        kw = (self.ed_search.text() or "").strip().lower()

        rows: List[offline.PackInfo] = []
        for p in self._packs:
            if lang and lang not in (p.from_code, p.to_code):
                continue
            if kw:
                hay = "%s %s %s %s %s %s" % (
                    p.from_code, p.to_code, p.from_name.lower(), p.to_name.lower(),
                    offline.lang_name(p.from_code), offline.lang_name(p.to_code))
                if kw not in hay.lower():
                    continue
            rows.append(p)

        rows.sort(key=lambda p: (
            0 if p.to_code in ("zh", "zt") else 1,
            offline.lang_name(p.from_code), offline.lang_name(p.to_code)))

        colors = theme.current_palette()
        self.table.setRowCount(len(rows))
        for i, p in enumerate(rows):
            pair = QTableWidgetItem("%s → %s" % (offline.lang_name(p.from_code),
                                                 offline.lang_name(p.to_code)))
            pair.setData(Qt.UserRole, (p.from_code, p.to_code))
            self.table.setItem(i, _COL_PAIR, pair)

            size = self._sizes.get(p.url)
            size_item = QTableWidgetItem("%.0f MB" % size if size else "—")
            size_item.setForeground(QBrush(QColor(colors.get("text_dim", "#8A8A8E"))))
            self.table.setItem(i, _COL_SIZE, size_item)

            installed = p.pair in self._installed
            state = QTableWidgetItem("已安装" if installed else "未安装")
            state.setForeground(QBrush(QColor(
                colors.get("ok", "#34C759") if installed else colors.get("text_dim", "#8A8A8E"))))
            self.table.setItem(i, _COL_STATE, state)

        self._update_buttons()

    # ---------------------------------------------------------------- 体积

    @staticmethod
    def _size_cache_path():
        return paths.cache_dir() / "argos_pack_sizes.json"

    def _load_size_cache(self) -> Dict[str, float]:
        try:
            return json.loads(self._size_cache_path().read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_size_cache(self) -> None:
        try:
            self._size_cache_path().write_text(
                json.dumps(self._sizes, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _fetch_sizes(self, packs: List[offline.PackInfo]) -> None:
        """后台补全体积（每个只做一次 HEAD，结果落盘缓存）。"""
        found: Dict[str, float] = {}
        stop = self._stop
        for p in packs:
            if stop.is_set():
                return
            if p.url in self._sizes:
                continue
            try:
                req = urllib.request.Request(
                    p.url, method="HEAD",
                    headers={"User-Agent": offline.USER_AGENT})
                with urllib.request.urlopen(req, timeout=25,
                                            context=offline._SSL) as r:  # noqa: SLF001
                    n = int(r.headers.get("Content-Length") or 0)
                if n:
                    found[p.url] = n / 1048576
            except Exception:
                continue
        if found and not stop.is_set():
            self.sizes_ready.emit(found)

    def _on_sizes_ready(self, found: dict) -> None:
        if not found:
            return
        self._sizes.update(found)
        self._save_size_cache()
        self._populate()

    # ---------------------------------------------------------------- 操作

    def _selected_pairs(self) -> List[Tuple[str, str]]:
        out = []
        for item in self.table.selectedItems():
            if item.column() != _COL_PAIR:
                continue
            data = item.data(Qt.UserRole)
            if data:
                out.append(tuple(data))
        return out

    def _pack_for(self, pair: Tuple[str, str]) -> Optional[offline.PackInfo]:
        for p in self._packs:
            if p.pair == pair:
                return p
        return None

    def _update_buttons(self) -> None:
        pairs = self._selected_pairs()
        has_new = any(p not in self._installed for p in pairs)
        has_old = any(p in self._installed for p in pairs)
        self.btn_download.setEnabled(has_new and not self._busy)
        self.btn_delete.setEnabled(has_old and not self._busy)

    def _download_selected(self) -> None:
        pairs = [p for p in self._selected_pairs() if p not in self._installed]
        if not pairs:
            return
        packs = [pp for pp in (self._pack_for(p) for p in pairs) if pp]
        if not packs:
            return

        self._busy = True
        self._cancel = False
        self.bar_progress.setVisible(True)
        self.bar_progress.setValue(0)
        self.btn_download.setEnabled(False)
        self.btn_delete.setEnabled(False)

        total = len(packs)
        stop = self._stop

        def work():
            for i, p in enumerate(packs):
                if stop.is_set():
                    return
                label = "%s → %s" % (offline.lang_name(p.from_code),
                                     offline.lang_name(p.to_code))

                def progress(pct, note, i=i, label=label):
                    if stop.is_set():
                        return
                    overall = int((i + pct / 100.0) * 100 / total)
                    self.progress_value.emit(
                        overall, "[%d/%d] %s · %s" % (i + 1, total, label, note))

                try:
                    offline.install_pack(p, progress=progress,
                                         cancelled=lambda: self._cancel or stop.is_set())
                    if not stop.is_set():
                        self.progress_value.emit(
                            int((i + 1) * 100 / total),
                            "[%d/%d] %s · 完成" % (i + 1, total, label))
                except Exception as e:  # noqa: BLE001
                    if not stop.is_set():
                        self.progress_value.emit(
                            int((i + 1) * 100 / total),
                            "[%d/%d] %s · 失败：%s"
                            % (i + 1, total, label, str(e)[:120]))
            if not stop.is_set():
                self.download_done.emit()

        threading.Thread(target=work, daemon=True).start()

    def _on_progress(self, value: int, text: str) -> None:
        self.bar_progress.setValue(value)
        self.lbl_status.setText(text)

    def _on_download_done(self) -> None:
        self._busy = False
        self.bar_progress.setVisible(False)
        self._refresh_installed()
        self._populate()
        self._update_buttons()
        self.changed.emit()

    def _delete_selected(self) -> None:
        pairs = [p for p in self._selected_pairs() if p in self._installed]
        if not pairs:
            return
        names = "、".join("%s → %s" % (offline.lang_name(a), offline.lang_name(b))
                         for a, b in pairs)
        if QMessageBox.question(self, "删除语言包",
                                "确定要删除以下语言包吗？\n\n%s" % names,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        ok = 0
        for a, b in pairs:
            if offline.remove_pack(a, b):
                ok += 1
        self.lbl_status.setText("已删除 %d 个语言包" % ok)
        self._refresh_installed()
        self._populate()
        self.changed.emit()

    def _open_dir(self) -> None:
        import os

        try:
            os.startfile(str(offline.models_root()))  # noqa: S606
        except Exception:
            pass

    # ---------------------------------------------------------------- 关闭

    def closeEvent(self, ev):
        self._cancel = True
        self._stop.set()
        super().closeEvent(ev)
