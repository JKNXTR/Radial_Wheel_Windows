"""Защита на ресурсите: инструментът е лек и предвидим.

* GPU: принудителен софтуерен (raster) рендер – колелото не зависи от графичната карта и драйверите ѝ.
* CPU: приоритет „над нормален“ (отзивчив интерфейс при натоварен компютър), но никога „реално време“.
* RAM: минимален работен набор (да не се изхвърля на диска) + периодична проверка; при надхвърляне на
  лимита се изчистват кешовете и се освобождава паметта. Реално „резервиране“ на RAM не се прави – то би
  отнело памет от останалите програми; вместо това инструментът държи собственото си потребление ниско.
"""
import gc
import logging
import os
import sys

from PySide6.QtCore import QTimer

log = logging.getLogger(__name__)
RAM_SOFT_MB = 220          # над това се чистят кешовете
RAM_HARD_MB = 400          # над това се записва предупреждение в лога
CHECK_MS = 30_000


def prepare_environment():
    """Извиква се преди QApplication."""
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")


def _win_tune():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetCurrentProcess()
        k.SetPriorityClass(h, 0x00008000)                         # ABOVE_NORMAL_PRIORITY_CLASS
        k.SetProcessWorkingSetSize(h, 24 * 1024 * 1024, 256 * 1024 * 1024)   # мин. 24 MB, макс. 256 MB
    except Exception:
        log.exception("Настройка на приоритета/паметта неуспешна")


def rss_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1048576.0
    except Exception:
        return 0.0


def trim():
    """Изчиства кешовете и освобождава памет."""
    try:
        from . import icons
        icons.clear_cache()
    except Exception:
        log.exception("Чистене на кеша неуспешно")
    gc.collect()


def check():
    mb = rss_mb()
    if mb > RAM_HARD_MB:
        log.warning("Висока памет: %.0f MB (лимит %d MB)", mb, RAM_HARD_MB)
    if mb > RAM_SOFT_MB:
        trim()
        log.info("Кешовете са изчистени: %.0f MB -> %.0f MB", mb, rss_mb())
    return mb


def start(parent):
    _win_tune()
    t = QTimer(parent)
    t.setInterval(CHECK_MS)
    t.timeout.connect(check)
    t.start()
    parent._resource_timer = t
