"""Зареждане/рендериране на икони (SVG, PNG, ICO, системни икони на файлове)."""
import os
from functools import lru_cache

from PySide6.QtCore import QByteArray, QFileInfo, QSize, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFileIconProvider

from .paths import ICONS

IMAGE_EXT = {".png", ".svg", ".ico", ".jpg", ".jpeg", ".bmp", ".webp"}
_provider = None


def builtin(name: str) -> str:
    return str(ICONS / f"{name}.svg")


def _render_svg(path: str, px: int, dpr: float) -> QPixmap:
    size = int(round(px * dpr))
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    try:
        with open(path, "rb") as f:
            r = QSvgRenderer(QByteArray(f.read()))
    except OSError:
        return QPixmap()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    r.render(p)
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    return pm


@lru_cache(maxsize=512)
def _cached(src: str, px: int, dpr: float, mtime: float) -> QPixmap:
    global _provider
    ext = os.path.splitext(src)[1].lower()
    if ext == ".svg":
        return _render_svg(src, px, dpr)
    if ext in IMAGE_EXT:
        pm = QPixmap(src)
        if pm.isNull():
            return pm
        pm = pm.scaled(int(px * dpr), int(px * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        return pm
    # системна икона на файл/папка/програма
    if _provider is None:
        _provider = QFileIconProvider()
    icon = _provider.icon(QFileInfo(os.path.expandvars(src)))
    return icon.pixmap(QSize(px, px), dpr)


def pixmap(src: str, px: int, dpr: float = 1.0) -> QPixmap:
    """`src` е абсолютен път към .svg/.png/.ico или към произволен файл/папка (системна икона)."""
    if not src:
        return QPixmap()
    real = os.path.expandvars(src)
    try:
        mt = os.path.getmtime(real)
    except OSError:
        mt = 0.0
    return _cached(real, int(px), float(dpr), mt)


def clear_cache():
    _cached.cache_clear()
