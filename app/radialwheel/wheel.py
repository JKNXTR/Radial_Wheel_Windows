"""Радиалното колело: 8 сектора по 45°, централен бутон, hit-testing с atan2/hypot (спец. модул А)."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QWidget

from . import icons
from .i18n import tr

INNER_RATIO = 0.39      # вътрешен кръг ≈ 35–40 % от диаметъра (спец. 2.2)
ICON_RATIO = 0.16      # размер на иконите спрямо диаметъра
CENTER = -2             # специално „активно“ състояние: централният бутон
NONE = -1


def sector_at(dx: float, dy: float) -> int:
    """Индекс на сектор 0..7 (0 = 12:00, по часовниковата стрелка) за вектор от центъра. Без мъртви зони."""
    ang = math.degrees(math.atan2(dx, -dy)) % 360.0     # 0° = нагоре, по часовниковата
    return int(((ang + 22.5) % 360.0) // 45.0)


class WheelWidget(QWidget):
    hovered = Signal(int)          # NONE / CENTER / 0..7 (след hover delay)
    sectorClicked = Signal(int)
    centerClicked = Signal()
    rightClicked = Signal()
    outsideClicked = Signal()      # клик във ъглите на widget-а, извън кръга

    def __init__(self, theme, diameter: int, sector_icons: list, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.D = diameter
        self.pad = max(10, int(diameter * 0.05))
        self.setFixedSize(diameter + 2 * self.pad, diameter + 2 * self.pad)
        self.setMouseTracking(True)
        self.sector_icons = sector_icons         # списък от 8 пътя към икони (по позиции)
        self.hover_delay = 80
        self.active = NONE                       # избран сектор (остава „залепнал“ извън кръга)
        self.locked = False                      # фиксиран панел (Click-to-Pin): hover не сменя избора
        self.center_hot = False
        self._armed = False                      # центърът е неутрален, докато курсорът не излезе от него
        self._pending = NONE
        self._spawn = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._commit)

    # ------------------------------------------------------------ геометрия
    @property
    def c(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    @property
    def R(self) -> float:
        return self.D / 2

    @property
    def r(self) -> float:
        return self.R * INNER_RATIO

    def reset_state(self):
        self._timer.stop()
        self.active = NONE
        self.center_hot = False
        self._armed = False
        self._spawn = None
        self._pending = NONE
        self.locked = False
        self.update()

    # ------------------------------------------------------------ вход
    def _classify(self, pos: QPointF):
        dx, dy = pos.x() - self.c.x(), pos.y() - self.c.y()
        dist = math.hypot(dx, dy)
        if dist < self.r:
            return CENTER
        if dist <= self.R:
            return sector_at(dx, dy)
        return None   # извън колелото -> без промяна (залепнал избор)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if not self._armed:
            # курсорът се появява върху центъра: активираме го (червен Delete) щом реално се помръдне
            if self._spawn is None:
                self._spawn = pos
            elif math.hypot(pos.x() - self._spawn.x(), pos.y() - self._spawn.y()) >= 3:
                self._armed = True
        self.track(pos)

    def track(self, pos: QPointF):
        if self.locked:
            return
        state = self._classify(pos)
        if state is None:
            self._timer.stop()
            self._pending = NONE
            return
        if state != CENTER:
            self._armed = True
        if state == CENTER and not self._armed:
            return                                # още не е излизал от центъра – остава неутрален
        current = CENTER if self.center_hot else self.active
        if state == current:
            self._timer.stop()
            self._pending = NONE
            return
        if state == self._pending and self._timer.isActive():
            return
        self._pending = state
        delay = 0 if state == CENTER else self.hover_delay
        if delay <= 0:
            self._commit()
        else:
            self._timer.start(delay)

    def _commit(self):
        state = self._pending
        self._pending = NONE
        if state == CENTER:
            self.center_hot = True
            self.active = NONE
        else:
            self.center_hot = False
            self.active = state
        self.update()
        self.hovered.emit(CENTER if state == CENTER else state)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.rightClicked.emit()
            return
        if e.button() != Qt.LeftButton:
            return
        state = self._classify(e.position())
        if state is None:
            self.outsideClicked.emit()
        elif state == CENTER:
            self.centerClicked.emit()
        elif state >= 0:
            if state != self.active:        # клик върху сектор го избира веднага
                self._timer.stop()
                self.locked = False
                self._pending = state
                self._commit()
            self.sectorClicked.emit(state)

    # ------------------------------------------------------------ рисуване
    def _sector_path(self, i: int) -> QPainterPath:
        R, r, c = self.R, self.r, self.c
        outer = QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R)
        inner = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        start = 90.0 - i * 45.0 - 22.5          # Qt: градуси обратно на часовниковата от 3:00
        p = QPainterPath()
        p.arcMoveTo(outer, start)
        p.arcTo(outer, start, 45.0)
        p.arcTo(inner, start + 45.0, -45.0)
        p.closeSubpath()
        return p

    def paintEvent(self, _):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        R, r, c = self.R, self.r, self.c

        # мека падаща сянка
        for k in range(8, 0, -1):
            col = QColor(0, 0, 0, 5 + (8 - k) * 2)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            rr = R + k * (self.pad / 9.0)
            p.drawEllipse(QPointF(c.x(), c.y() + self.pad * 0.25), rr, rr)

        # неактивни сектори
        body = QLinearGradient(0, c.y() - R, 0, c.y() + R)
        body.setColorAt(0, QColor(t.wheel_top))
        body.setColorAt(1, QColor(t.wheel_bottom))
        line = QPen(QColor(t.sector_line), max(1.6, self.D * 0.007))
        line.setJoinStyle(Qt.RoundJoin)
        for i in range(8):
            if i == self.active:
                continue
            p.setPen(line)
            p.setBrush(body)
            p.drawPath(self._sector_path(i))

        # активен сектор
        if self.active >= 0:
            path = self._sector_path(self.active)
            br = path.boundingRect()
            g = QLinearGradient(0, br.top(), 0, br.bottom())
            g.setColorAt(0, QColor(t.active_top))
            g.setColorAt(1, QColor(t.active_bottom))
            pen = QPen(QColor(t.active_border), max(1.6, self.D * 0.007))
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(g)
            p.drawPath(path)

        # външен кант
        p.setPen(QPen(QColor(t.wheel_border), max(1.5, self.D * 0.006)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, R, R)

        # икони
        mid = (R + r) / 2
        px = int(self.D * ICON_RATIO)
        dpr = self.devicePixelRatioF()
        for i, src in enumerate(self.sector_icons):
            a = math.radians(i * 45.0)
            ic = QPointF(c.x() + mid * math.sin(a), c.y() - mid * math.cos(a))
            pm = icons.pixmap(src, px, dpr)
            if not pm.isNull():
                p.drawPixmap(int(ic.x() - px / 2), int(ic.y() - px / 2), pm)

        # централен кръг
        if self.center_hot:
            self._draw_center(p, QColor(t.delete_top), QColor(t.delete_bottom), QColor("#E86A6A"))
            p.setPen(QColor("#FFFFFF"))
            f = QFont("Segoe UI")
            f.setPixelSize(max(10, int(self.D * 0.078)))
            p.setFont(f)
            p.drawText(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), Qt.AlignCenter, tr("center.delete"))
        else:
            self._draw_center(p, QColor(t.center_top), QColor(t.center_bottom), QColor(255, 255, 255, 38))
        p.end()

    def _draw_center(self, p: QPainter, top: QColor, bottom: QColor, rim: QColor):
        c, r = self.c, self.r
        # външна лека сянка
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawEllipse(QPointF(c.x(), c.y() + r * 0.04), r * 1.02, r * 1.02)
        g = QLinearGradient(0, c.y() - r, 0, c.y() + r)
        g.setColorAt(0, top)
        g.setColorAt(1, bottom)
        p.setBrush(g)
        p.setPen(QPen(QColor(0, 0, 0, 140), 1.4))
        p.drawEllipse(c, r, r)
        # скосен ръб (bevel)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(rim, max(1.2, r * 0.035)))
        p.drawArc(QRectF(c.x() - r + 2, c.y() - r + 2, 2 * r - 4, 2 * r - 4), 30 * 16, 120 * 16)
        shade = QRadialGradient(c.x(), c.y() + r * 0.5, r * 1.1)
        shade.setColorAt(0, QColor(0, 0, 0, 0))
        shade.setColorAt(1, QColor(0, 0, 0, 55))
        p.setPen(Qt.NoPen)
        p.setBrush(shade)
        p.drawEllipse(c, r - 1, r - 1)
