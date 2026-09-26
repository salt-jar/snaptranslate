# -*- coding: utf-8 -*-
"""图像预处理：放大 + 增强，显著提升小字号 / 深色主题截图的识别率。"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def _qimage_png(qimg) -> Optional[bytes]:
    """纯 Qt 路径的 PNG 编码（OpenCV 不可用时使用）。"""
    from PyQt5.QtCore import QBuffer, QByteArray, QIODevice

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    ok = qimg.save(buf, "PNG")
    buf.close()
    return bytes(ba) if ok else None


def qimage_to_bgr(qimg) -> np.ndarray:
    """QImage -> OpenCV BGR ndarray。

    QImage 的 ``bytesPerLine`` 有 4 字节对齐填充，必须先按行切开再裁掉填充，
    否则图形宽度不是 4 的倍数时整幅图会错位。
    """
    from PyQt5.QtGui import QImage

    img = qimg.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    ptr = img.constBits()
    try:
        ptr.setsize(img.sizeInBytes())
    except AttributeError:          # Qt < 5.10
        ptr.setsize(img.byteCount())
    arr = np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine())
    arr = arr[:, : w * 3].reshape(h, w, 3)
    return arr[:, :, ::-1].copy()   # RGB -> BGR


def prepare_png(qimg, upscale: float = 2.0, threshold: int = 900,
                enhance: bool = True) -> Tuple[Optional[bytes], float]:
    """把 QImage 处理成适合 OCR 的 PNG 字节，返回 ``(png_bytes, 实际放大倍数)``。

    OpenCV 不可用时退化为原图直接编码，功能不受影响，只是少了增强效果。
    """
    try:
        import cv2
    except Exception:
        return _qimage_png(qimg), 1.0

    img = qimage_to_bgr(qimg)
    h, w = img.shape[:2]
    actual = 1.0

    if upscale and upscale > 1.0 and max(h, w) < threshold:
        want = float(upscale)
        if max(h, w) * want > 4000:                 # 限制尺寸，避免识别过慢
            want = max(1.0, 4000.0 / max(h, w))
        if want > 1.01:
            img = cv2.resize(img, None, fx=want, fy=want, interpolation=cv2.INTER_CUBIC)
            actual = want

    if enhance:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 深色主题（浅字深底）先反色：OCR 模型对"深字浅底"敏感得多
        if float(gray.mean()) < 96:
            gray = cv2.bitwise_not(gray)
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    ok, buf = cv2.imencode(".png", img)
    if not ok:
        return _qimage_png(qimg), 1.0
    return buf.tobytes(), actual
