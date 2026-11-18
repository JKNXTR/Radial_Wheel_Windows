"""Рендира всички състояния на интерфейса (headless) в PNG – за сравнение с mockup-ите.

  python tools/render_states.py <изходна_папка> [scale]
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp()                       # не пипаме реалния конфиг
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from PySide6.QtCore import QPointF, Qt                          # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter              # noqa: E402
from PySide6.QtWidgets import QApplication                      # noqa: E402

from radialwheel import audio                                      # noqa: E402
from radialwheel.config import cfg                              # noqa: E402
from radialwheel.i18n import set_language                       # noqa: E402
from radialwheel.overlay import Overlay                         # noqa: E402
from radialwheel.wheel import CENTER                            # noqa: E402


audio.snapshot = lambda: {"vol": 75, "muted": False, "ready": True, "default": "a", "devices": [
    ("a", "Слушалки (headphones)"), ("b", "Говорители (speakers)"), ("c", "Speakers (Realtek)"), ("d", "Headphones (Bluetooth)")]}   # демо стойности


class FakeController:
    def notify(self, *a):
        print("notify:", a)

    def open_settings(self, p):
        print("settings", p)


def grab(ov, path):
    pm = ov.grab()
    img = QImage(pm.size(), QImage.Format_ARGB32)
    img.fill(QColor("#C6C6C6"))
    p = QPainter(img)
    p.drawPixmap(0, 0, pm)
    p.end()
    img.save(str(path))


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "renders")
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    cfg.load()
    if len(sys.argv) > 2:
        cfg["appearance"]["scale"] = float(sys.argv[2])
    cfg["behavior"]["hover_delay_ms"] = 0
    set_language("bg")
    Overlay._fit_scale = lambda self, screen: cfg["appearance"]["scale"]   # offscreen екранът е само 800x600
    ov = Overlay(FakeController())
    ov.setWindowOpacity(1.0)
    ov.show()
    w = ov.wheel
    order = cfg["sector_order"]
    for idx, sid in enumerate(order):
        w.reset_state()
        w._armed = True
        # позиция на курсора в средата на сектора
        import math
        a = math.radians(idx * 45)
        r = (w.R + w.r) / 2
        w.track(QPointF(w.c.x() + r * math.sin(a), w.c.y() - r * math.cos(a)))
        app.processEvents()
        grab(ov, out / f"{idx + 1:02d}_{sid}.png")
    w.reset_state()
    w._armed = True
    w.track(QPointF(w.c.x(), w.c.y()))
    app.processEvents()
    grab(ov, out / "09_center_delete.png")
    w.reset_state()
    app.processEvents()
    grab(ov, out / "10_idle.png")
    print("OK ->", out)


if __name__ == "__main__":
    main()
