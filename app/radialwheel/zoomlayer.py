"""Слой над колелото: избраният сектор (с иконата си) плавно се увеличава ZOOM пъти; при преминаване към
друг сектор предишният плавно се връща към оригиналните си размер и позиция.

Слоят е прозрачен за мишката и е под панелите. Рисува се върху колелото, така че нищо в колелото не се променя."""
import math

from PySide6.QtCore import QElapsedTimer, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QTransform
from PySide6.QtWidgets import QWidget

from . import icons
from .config import cfg
from .wheel import ICON_RATIO

TAU_MS = 70.0         # времева константа на плавността при скорост 100 % (по-малко = по-бързо)


class ZoomLayer(QWidget):
    def __init__(self, wheel, parent):
        super().__init__(parent)
        self.wheel = wheel
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setGeometry(parent.rect())
        self.z = [0.0] * 8
        self.dim = 0.0
        wheel.fx = self
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        wheel.changed.connect(self.kick)
        self.show()
        self.raise_()

    @staticmethod
    def enabled():
        return bool(cfg["appearance"]["animations"])

    def target(self, i):
        w = self.wheel
        if not (self.enabled() and cfg["animation"]["zoom_on"]):
            return 0.0
        return 1.0 if (w.active == i and not w.center_hot) else 0.0

    def dim_target(self):
        w = self.wheel
        an = cfg["animation"]
        return 1.0 if (self.enabled() and an["dim_on"] and w.active >= 0 and not w.center_hot) else 0.0

    def zoom_of(self, i):
        order = cfg["sector_order"]
        return float(cfg["animation"]["zoom"].get(order[i], 2.0)) if i < len(order) else 2.0

    def kick(self):
        if not self._timer.isActive():
            self._clock.start()
            self._timer.start()

    def _tick(self):
        dt = max(1, self._clock.restart())
        k = 1.0 - math.exp(-dt / (TAU_MS * 100.0 / cfg["animation"]["speed"]))
        busy = False
        dd = self.dim_target() - self.dim
        if abs(dd) < 0.004:
            self.dim = self.dim_target()
        else:
            self.dim += dd * k
            busy = True
        self.wheel.update()
        for i in range(8):
            t = self.target(i)
            d = t - self.z[i]
            if abs(d) < 0.004:
                self.z[i] = t
            else:
                self.z[i] += d * k
                busy = True
        self.update()
        if not busy:
            self._timer.stop()

    def paintEvent(self, _):
        w = self.wheel
        order = sorted((i for i in range(8) if self.z[i] > 0.004), key=lambda i: self.z[i])
        if not order:
            return
        t = w.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        off = w.pos()
        R, r = w.R, w.r
        mid = (R + r) / 2
        px = int(w.D * ICON_RATIO)
        dpr = self.devicePixelRatioF()
        for i in order:
            z = self.z[i]
            sc = 1.0 + (self.zoom_of(i) - 1.0) * z
            a = math.radians(i * 45.0)
            push = (cfg["animation"]["push"] / 100.0 * R * z) if cfg["animation"]["push_on"] else 0.0
            piv = QPointF(w.c.x() + mid * math.sin(a), w.c.y() - mid * math.cos(a))      # центроид на сектора (в координати на колелото)
            shift = QPointF(push * math.sin(a), -push * math.cos(a))                    # отдалечаване от центъра
            path = w._sector_path(i).translated(shift)
            piv = piv + shift
            tr_ = QTransform()
            tr_.translate(off.x() + piv.x(), off.y() + piv.y())
            tr_.scale(sc, sc)
            tr_.translate(-piv.x(), -piv.y())
            big = tr_.map(path.translated(off.x() * 0, off.y() * 0))
            # сянка
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, int(90 * min(1.0, z))))
            p.drawPath(big.translated(0, w.D * 0.012 * z))
            # тяло на сектора
            br = big.boundingRect()
            g = QLinearGradient(0, br.top(), 0, br.bottom())
            top, bot = QColor(t.active_top), QColor(t.active_bottom)
            g.setColorAt(0, top)
            g.setColorAt(1, bot)
            pen = QPen(QColor(t.active_border), max(1.6, w.D * 0.007))
            pen.setJoinStyle(Qt.RoundJoin)
            p.setOpacity(min(1.0, z * 2.5))
            p.setPen(pen)
            p.setBrush(g)
            p.drawPath(big)
            # икона
            if i < len(w.sector_icons):
                size = int(px * sc)
                pm = icons.pixmap(w.sector_icons[i], size, dpr)
                if not pm.isNull():
                    c = QPointF(off.x() + piv.x(), off.y() + piv.y())
                    p.setOpacity(1.0)
                    p.drawPixmap(int(c.x() - size / 2), int(c.y() - size / 2), pm)
            p.setOpacity(1.0)
        p.end()
