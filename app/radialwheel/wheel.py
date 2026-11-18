"""Радиалното колело: 8 сектора по 45°, централен бутон, hit-testing с atan2/hypot (спец. модул А)."""
import math

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QWidget

from . import icons
from .config import cfg
from .i18n import tr

INNER_RATIO = 0.39      # вътрешен кръг ≈ 35–40 % от диаметъра (спец. 2.2)
ICON_RATIO = 0.16      # размер на иконите спрямо диаметъра
CENTER = -2             # специално „активно“ състояние: централният бутон
NONE = -1
HOLD_MS = 1000          # задържане на центъра за Delete (кратък клик = Backspace)


def sector_at(dx: float, dy: float) -> int:
    """Индекс на сектор 0..7 (0 = 12:00, по часовниковата стрелка) за вектор от центъра. Без мъртви зони."""
    ang = math.degrees(math.atan2(dx, -dy)) % 360.0     # 0° = нагоре, по часовниковата
    return int(((ang + 22.5) % 360.0) // 45.0)


class WheelWidget(QWidget):
    hovered = Signal(int)          # NONE / CENTER / 0..7 (след hover delay)
    sectorClicked = Signal(int)
    centerClicked = Signal()       # кратък клик върху центъра -> Backspace
    centerHeld = Signal()          # задържане ~1 s (пълен пръстен) -> Delete
    rightClicked = Signal()
    changed = Signal()             # сменен активен сектор / център (за анимацията на увеличението)
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
        self._hold = 0.0                         # 0..1 прогрес на пръстена при задържане на центъра
        self._holding = False
        self._hold_clock = QElapsedTimer()
        self._hold_timer = QTimer(self)
        self._hold_timer.setInterval(16)
        self._hold_timer.timeout.connect(self._hold_tick)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._commit)
        self.fx = None                           # ZoomLayer: z[i] (увеличение на сектор) и dim (затъмняване на останалите)
        self._ct = 0.0                           # 0..1 плавно червено светене на центъра
        self._hb = 0.0                           # 0..1 изгладен прогрес на задържането (яркост/размер)
        self._lt = 0.0                           # 0..1 изгладен прогрес за смяна на надписа Backspace -> Delete
        self._cclock = QElapsedTimer()
        self._ctimer = QTimer(self)
        self._ctimer.setInterval(16)
        self._ctimer.timeout.connect(self._ctick)

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

    def _ctick(self):
        """Плавна анимация на централния бутон: червено светене и (при задържане) яркост + лек растеж."""
        an = cfg["animation"]
        on = bool(cfg["appearance"]["animations"])
        dt = max(1, self._cclock.restart())
        k = 1.0 - math.exp(-dt / (110.0 * 100.0 / an["speed"]))
        tgt = 1.0 if self.center_hot else 0.0
        htg = self._hold if (on and an["center_boost"]) else 0.0
        if not (on and an["center_glow"]):
            self._ct = tgt
        else:
            self._ct += (tgt - self._ct) * k
        self._hb += (htg - self._hb) * min(1.0, k * 1.6)
        self._lt += (self._hold - self._lt) * min(1.0, k * 2.2)
        done = (abs(tgt - self._ct) < 0.004 and abs(htg - self._hb) < 0.004 and abs(self._hold - self._lt) < 0.004
                and not self._holding)
        if done:
            self._ct, self._hb, self._lt = tgt, htg, self._hold
            self._ctimer.stop()
        self.update()

    def _kick_center(self):
        if not self._ctimer.isActive():
            self._cclock.start()
            self._ctimer.start()

    def _hold_start(self):
        self._holding = True
        self._hold = 0.0
        self._kick_center()
        self._hold_clock.start()
        self._hold_timer.start()

    def _hold_cancel(self):
        self._hold_timer.stop()
        self._holding = False
        if self._hold:
            self._hold = 0.0
            self.update()

    def _hold_tick(self):
        self._hold = min(1.0, self._hold_clock.elapsed() / HOLD_MS)
        self.update()
        if self._hold >= 1.0:
            self._hold_timer.stop()
            self._holding = False
            self._hold_done = True
            self.centerHeld.emit()
            self._hold = 0.0
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not self._holding:
            return
        self._hold_cancel()                        # пуснат преди да се напълни -> кратък клик
        if self._classify(e.position()) == CENTER:
            self.centerClicked.emit()

    def reset_state(self):
        self._hold_cancel()
        self._timer.stop()
        self.active = NONE
        self.center_hot = False
        self._armed = False
        self._spawn = None
        self._pending = NONE
        self.locked = False
        self._ct = self._hb = self._lt = 0.0
        self.update()
        self.changed.emit()

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
        if self._holding and state != CENTER:
            self._hold_cancel()
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
        self._kick_center()
        self.update()
        self.changed.emit()
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
            self._hold_start()
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

    def _sector_opacity(self, i, fx, dim_amt):
        """Непрозрачност на неизбран сектор: плавно намалява, докато някой сектор е избран."""
        if fx is None:
            return 1.0
        return 1.0 - dim_amt * fx.dim * (1.0 - fx.z[i])

    @staticmethod
    def _mix(a: QColor, b: QColor, t: float) -> QColor:
        return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                      int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))

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
        fx = self.fx
        dim_amt = cfg["animation"]["dim"] / 100.0
        for i in range(8):
            if i == self.active:
                continue
            p.setOpacity(self._sector_opacity(i, fx, dim_amt))
            p.setPen(line)
            p.setBrush(body)
            p.drawPath(self._sector_path(i))
        p.setOpacity(1.0)

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
                p.setOpacity(self._sector_opacity(i, fx, dim_amt) if i != self.active else 1.0)
                p.drawPixmap(int(ic.x() - px / 2), int(ic.y() - px / 2), pm)
        p.setOpacity(1.0)

        # централен кръг: плавен преход сивo -> червено; при задържане по-ярко червено и леко увеличение
        ct, hb = self._ct, self._hb
        re = r * (1.0 + 0.07 * hb)
        top = self._mix(QColor(t.center_top), QColor(t.delete_top), ct)
        bot = self._mix(QColor(t.center_bottom), QColor(t.delete_bottom), ct)
        rim = self._mix(QColor(255, 255, 255, 38), QColor("#E86A6A"), ct)
        if hb > 0:
            top, bot = self._mix(top, QColor("#FF6A5C"), hb * 0.75), self._mix(bot, QColor("#FF3B30"), hb * 0.75)
            rim = self._mix(rim, QColor("#FFB1A8"), hb)
        if ct > 0.02:                                     # мека червена аура около бутона
            for k in range(6, 0, -1):
                glow = QColor(255, 60, 50, int((10 + 22 * hb) * ct * (7 - k) / 6.0))
                p.setPen(Qt.NoPen)
                p.setBrush(glow)
                rr = re + k * r * 0.045
                p.drawEllipse(c, rr, rr)
        self._draw_center(p, top, bot, rim, re)
        if ct > 0.02:
            # надпис: първоначално Backspace; по време на задържане плавно се сменя с Delete (на текущия език)
            mix = max(0.0, min(1.0, (self._lt - 0.12) / 0.38))
            area = QRectF(c.x() - re, c.y() - re, 2 * re, 2 * re)
            for text, alpha in ((tr("center.backspace"), 1.0 - mix), (tr("center.delete"), mix)):
                if alpha <= 0.01:
                    continue
                tc = QColor("#FFFFFF")
                tc.setAlpha(int(255 * min(1.0, ct * 1.3) * alpha))
                p.setPen(tc)
                f = QFont("Segoe UI")
                px = max(9, int(self.D * 0.078 * (1.0 + 0.07 * hb)))
                f.setPixelSize(px)
                while px > 9 and QFontMetricsF(f).horizontalAdvance(text) > re * 1.62:      # дългият надпис се вписва в кръга
                    px -= 1
                    f.setPixelSize(px)
                p.setFont(f)
                p.drawText(area, Qt.AlignCenter, text)
        if self._hold > 0:                        # пръстен по ръба: от 12:00 по часовниковата стрелка
            ring = max(3.0, re * 0.09)
            pen = QPen(QColor("#FF5448"), ring)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(c.x() - re + ring / 2, c.y() - re + ring / 2, 2 * re - ring, 2 * re - ring),
                      90 * 16, int(-self._hold * 360 * 16))
        p.end()

    def _draw_center(self, p: QPainter, top: QColor, bottom: QColor, rim: QColor, r=None):
        c = self.c
        r = self.r if r is None else r
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
