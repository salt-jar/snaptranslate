# -*- coding: utf-8 -*-
"""屏幕枚举与抓屏。

坐标有两套，必须区分清楚：

* **逻辑坐标**（Qt，logical）—— ``QScreen.geometry()``，受系统缩放影响。
  窗口、鼠标事件都用它。本机 150% 缩放时 2560x1600 物理 ≈ 1707x1067 逻辑。
* **物理坐标**（Win32 / mss，physical）—— 真实像素，抓屏图像用它。

``ScreenMapper`` 负责两者互转，比例是**实测计算**的（物理宽/逻辑宽），
因此不依赖任何假设的缩放参数。
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QGuiApplication, QImage


def enable_dpi_awareness() -> None:
    """必须在创建 QApplication 之前调用，否则抓屏会拿到被系统拉伸的模糊图。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


@dataclass
class Monitor:
    index: int
    phys: Tuple[int, int, int, int]     # left, top, width, height（物理像素）
    logical: QRect                      # Qt 逻辑坐标
    dpr: float

    @property
    def scale_x(self) -> float:
        return self.phys[2] / max(1, self.logical.width())

    @property
    def scale_y(self) -> float:
        return self.phys[3] / max(1, self.logical.height())


class ScreenMapper:
    """逻辑 <-> 物理 坐标换算，并负责抓取整个虚拟桌面。"""

    def __init__(self) -> None:
        self.monitors: List[Monitor] = []
        self.virtual_phys: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self.virtual_logical: QRect = QRect(0, 0, 0, 0)
        self.refresh()

    # ---------------------------------------------------------------- 构建

    def refresh(self) -> None:
        app = QGuiApplication.instance()
        screens = list(app.screens()) if app else []
        try:
            import mss

            with mss.mss() as sct:
                raw = list(sct.monitors)
        except Exception:
            raw = []

        if raw:
            self.virtual_phys = (
                raw[0]["left"], raw[0]["top"], raw[0]["width"], raw[0]["height"]
            )
            phys_list = sorted(raw[1:], key=lambda m: (m["left"], m["top"]))
        else:
            phys_list = []

        if screens:
            log_list = sorted(screens, key=lambda s: (s.geometry().x(), s.geometry().y()))
            union = QRect(log_list[0].geometry())
            for s in log_list[1:]:
                union = union.united(s.geometry())
            self.virtual_logical = union
        else:
            log_list = []

        self.monitors = []
        if phys_list and log_list and len(phys_list) == len(log_list):
            for i, (m, s) in enumerate(zip(phys_list, log_list), start=1):
                self.monitors.append(
                    Monitor(
                        index=i,
                        phys=(m["left"], m["top"], m["width"], m["height"]),
                        logical=QRect(s.geometry()),
                        dpr=float(s.devicePixelRatio()),
                    )
                )
        elif phys_list and self.virtual_logical.isValid():
            # 数量对不上（极少见）：退化成一个覆盖整个虚拟桌面的大显示器
            self.monitors.append(
                Monitor(
                    index=1,
                    phys=self.virtual_phys,
                    logical=self.virtual_logical,
                    dpr=float(log_list[0].devicePixelRatio()) if log_list else 1.0,
                )
            )

    # ---------------------------------------------------------------- 换算

    def _monitor_for(self, pt: QPoint) -> Optional[Monitor]:
        for m in self.monitors:
            if m.logical.contains(pt):
                return m
        return None

    @property
    def global_scale(self) -> Tuple[float, float]:
        lw = max(1, self.virtual_logical.width())
        lh = max(1, self.virtual_logical.height())
        return self.virtual_phys[2] / lw, self.virtual_phys[3] / lh

    def logical_to_phys(self, pt: QPoint) -> Tuple[int, int]:
        m = self._monitor_for(pt)
        if m is not None:
            sx, sy = m.scale_x, m.scale_y
            return (
                m.phys[0] + int(round((pt.x() - m.logical.x()) * sx)),
                m.phys[1] + int(round((pt.y() - m.logical.y()) * sy)),
            )
        sx, sy = self.global_scale
        return (
            self.virtual_phys[0] + int(round((pt.x() - self.virtual_logical.x()) * sx)),
            self.virtual_phys[1] + int(round((pt.y() - self.virtual_logical.y()) * sy)),
        )

    def logical_rect_to_phys(self, rect: QRect) -> QRect:
        """逻辑矩形 -> 物理矩形。

        使用「左闭右开」语义（宽 = x + width - x），这样拖动 520 个逻辑像素
        在 200% 缩放下正好得到 1040 个物理像素。若用 QRect 默认的闭区间语义
        （right = x + width - 1），每种缩放都会多切 1 像素。
        """
        r = rect.normalized()
        x0, y0 = self.logical_to_phys(QPoint(r.x(), r.y()))
        x1, y1 = self.logical_to_phys(QPoint(r.x() + r.width(), r.y() + r.height()))
        return QRect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))

    # ---------------------------------------------------------------- 抓屏

    def grab_virtual_desktop(self) -> Tuple[QImage, Tuple[int, int, int, int]]:
        """抓取整个虚拟桌面，返回 (QImage 物理像素, 物理矩形)。"""
        import mss

        with mss.mss() as sct:
            mon = sct.monitors[0]
            shot = sct.grab(mon)
            img = QImage(shot.bgra, shot.width, shot.height, QImage.Format_ARGB32)
            img = img.copy()   # 脱离 mss 的缓冲区
        return img, (mon["left"], mon["top"], mon["width"], mon["height"])

    def grab_region(self, rect_logical: QRect) -> QImage:
        """按逻辑矩形抓取指定区域（用于「重译上次区域」）。"""
        img, origin = self.grab_virtual_desktop()
        phys = self.logical_rect_to_phys(rect_logical)
        src = QRect(phys.x() - origin[0], phys.y() - origin[1],
                    phys.width(), phys.height())
        src = src.intersected(QRect(0, 0, img.width(), img.height()))
        if src.width() < 1 or src.height() < 1:
            return QImage()
        return img.copy(src)

    @property
    def effective_scale(self) -> float:
        """给界面显示用：100% / 150% ..."""
        sx, _ = self.global_scale
        return sx
