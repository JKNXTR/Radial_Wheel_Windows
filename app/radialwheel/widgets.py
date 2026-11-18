"""Повтарящи се елементи на панелите: рамки, плочки (tiles), клавишни бутони (keycaps)."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolTip, QWidget

from . import icons


def font(px: float, weight=QFont.Normal, family="Segoe UI") -> QFont:
    f = QFont(family)
    f.setPixelSize(max(8, int(round(px))))
    f.setWeight(weight)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


# ====================================================================== рамки
class Frame(QWidget):
    closeRequested = Signal()
    settingsRequested = Signal()

    """Тъмна заоблена рамка със заглавна лента. kind: 'global' (с падаща сянка) или 'sub' (вградена)."""

    def __init__(self, theme, s, title="", kind="global", parent=None):
        super().__init__(parent)
        self.theme, self.s, self.title, self.kind = theme, s, title, kind
        self.header_h = round((26 if kind == "global" else 24) * s) if title else 0
        self.pad = round(8 * s)
        self.shadow = round(6 * s) if kind == "global" else 0
        self._x_hover = False
        self._g_hover = False
        self.has_gear = False        # включва се от Overlay за панели с настройки
        self.has_close = kind == "global" and bool(title)
        if self.has_close:
            self.setMouseTracking(True)
        self.content = QWidget(self)
        self.content.setAttribute(Qt.WA_TranslucentBackground)
        self.layout_ = QHBoxLayout(self.content)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(round(6 * s))

    def _x_rect(self) -> QRectF:
        h = self.header_h
        return QRectF(self.width() - self.shadow - h, self.shadow, h, h)

    def _g_rect(self) -> QRectF:
        h = self.header_h
        return QRectF(self.shadow, self.shadow, h, h)

    def mouseMoveEvent(self, e):
        if self.has_close:
            hov = self._x_rect().contains(e.position())
            ghov = self.has_gear and self._g_rect().contains(e.position())
            if hov != self._x_hover or ghov != self._g_hover:
                self._x_hover, self._g_hover = hov, ghov
                self.update()

    def leaveEvent(self, e):
        if self._x_hover or self._g_hover:
            self._x_hover = self._g_hover = False
            self.update()

    def mousePressEvent(self, e):
        e.accept()          # клик върху празно място на панела не бива да затваря менюто
        if self.has_close and e.button() == Qt.LeftButton:
            if self._x_rect().contains(e.position()):
                self.closeRequested.emit()
            elif self.has_gear and self._g_rect().contains(e.position()):
                self.settingsRequested.emit()

    def resizeEvent(self, _):
        sh = self.shadow
        self.content.setGeometry(sh + self.pad, sh + self.header_h + self.pad,
                                 self.width() - 2 * (sh + self.pad),
                                 self.height() - 2 * sh - self.header_h - 2 * self.pad)

    def paintEvent(self, _):
        t, s = self.theme, self.s
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        sh = self.shadow
        rect = QRectF(sh, sh, self.width() - 2 * sh, self.height() - 2 * sh - 0)
        radius = (9 if self.kind == "global" else 7) * s
        if sh:
            for k in range(sh, 0, -1):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 14))
                p.drawRoundedRect(rect.adjusted(-k * 0.5, -k * 0.2, k * 0.5, k * 0.9), radius + k, radius + k)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        if self.kind == "global":
            g = QLinearGradient(0, rect.top(), 0, rect.bottom())
            g.setColorAt(0, QColor(t.panel_top))
            g.setColorAt(1, QColor(t.panel_bottom))
        else:
            g = QLinearGradient(0, rect.top(), 0, rect.bottom())
            g.setColorAt(0, QColor(t.tile_bg).lighter(108))
            g.setColorAt(1, QColor(t.tile_bg))
        p.fillPath(path, g)
        if self.header_h:
            p.save()
            p.setClipPath(path)
            hdr = QColor(t.header_bg)
            if self.kind == "sub":
                hdr = hdr.lighter(112) if t.name == "dark" else hdr
            p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), self.header_h), hdr)
            p.restore()
            p.setPen(QColor(t.text))
            tf = font(14 * s)
            p.setFont(tf)
            title = QFontMetrics(tf).elidedText(self.title, Qt.ElideRight, int(rect.width() - 12))
            p.drawText(QRectF(rect.left(), rect.top(), rect.width(), self.header_h), Qt.AlignCenter, title)
        if self.has_gear:                        # бърз пряк път към настройките на панела
            gr = self._g_rect()
            if self._g_hover:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(t.tile_hover) if t.name == "light" else QColor(255, 255, 255, 40))
                p.drawRoundedRect(gr.adjusted(4 * s, 3 * s, -4 * s, -3 * s), 4 * s, 4 * s)
            gpx = int(self.header_h * 0.62)
            pm = icons.pixmap(icons.builtin("sys_settings"), gpx, self.devicePixelRatioF())
            if not pm.isNull():
                p.drawPixmap(int(gr.center().x() - gpx / 2), int(gr.center().y() - gpx / 2), pm)
        if self.has_close:                       # бутон X за затваряне на панела (горе вдясно)
            xr = self._x_rect()
            if self._x_hover:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(t.delete_top))
                p.drawRoundedRect(xr.adjusted(5 * s, 4 * s, -5 * s, -4 * s), 4 * s, 4 * s)
            p.setPen(QPen(QColor("#FFFFFF" if self._x_hover else t.text), max(1.4, 1.6 * s), Qt.SolidLine, Qt.RoundCap))
            c, d = xr.center(), 4.2 * s
            p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
            p.drawLine(QPointF(c.x() - d, c.y() + d), QPointF(c.x() + d, c.y() - d))
        p.setPen(QPen(QColor(t.panel_border if self.kind == "global" else t.tile_border), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        inner = QPainterPath()
        inner.addRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1, radius - 1)
        p.setPen(QPen(QColor(255, 255, 255, 22 if t.name == "dark" else 90), 1))
        p.drawPath(inner)
        p.end()


# ====================================================================== плочка
class Tile(QWidget):
    clicked = Signal()
    contextRequested = Signal(object)       # глобална позиция
    dropped = Signal(str)                   # път на пуснат файл

    def __init__(self, theme, s, label="", icon_src="", tooltip="", parent=None, icon_ratio=0.50, flat=False, icon_px=0, label_px=0, bg=""):
        super().__init__(parent)
        self.theme, self.s, self.label, self.icon_src = theme, s, label, icon_src
        self.flat = flat
        self.icon_px, self.label_px = icon_px, label_px
        self.bg = bg                 # потребителски фон "#AARRGGBB" ("" = от темата)
        self.icon_ratio = icon_ratio
        self._hover = self._down = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(QSize(round(30 * s), round(30 * s)))
        self.setAcceptDrops(True)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon(self, src):
        self.icon_src = src
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = self._down = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._down = True
            self.update()
        elif e.button() == Qt.RightButton:
            self.contextRequested.emit(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._down:
            self._down = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.dropped.emit(urls[0].toLocalFile())
            e.acceptProposedAction()

    def paintEvent(self, _):
        t, s = self.theme, self.s
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if not self.flat or self._hover:
            bg = QColor(t.tile_hover if self._hover else t.tile_bg)
            if self.bg and QColor(self.bg).isValid():
                bg = QColor(self.bg)
                if self._hover:
                    bg = bg.lighter(125)
            if self._down:
                bg = bg.darker(120)
            p.setBrush(bg)
            p.setPen(QPen(QColor(t.active_border if self._hover else t.tile_border), 1.2))
            p.drawRoundedRect(r, 6 * s, 6 * s)
            p.setPen(QPen(QColor(255, 255, 255, 18 if t.name == "dark" else 80), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), 5 * s, 5 * s)

        fm_h = round(max(15 * s, (self.label_px or 0) * 1.25)) if self.label else 0
        avail_h = self.height() - fm_h - round(8 * s)
        px = self.icon_px or max(16, int(min(self.width() * 0.62, avail_h, self.height() * self.icon_ratio * 1.2)))
        top = (self.height() - fm_h - px) / 2 - (1 if self.label else 0)
        pm = icons.pixmap(self.icon_src, px, self.devicePixelRatioF()) if self.icon_src else None
        if pm is not None and not pm.isNull():
            p.drawPixmap(int((self.width() - px) / 2), int(top), pm)
        if self.label:
            size = self.label_px or 12.5 * s
            f = font(size)
            while QFontMetrics(f).horizontalAdvance(self.label) > self.width() - 6 and size > 9:
                size -= 0.5
                f = font(size)
            p.setFont(f)
            p.setPen(QColor(t.text))
            txt = QFontMetrics(f).elidedText(self.label, Qt.ElideRight, self.width() - 6)
            p.drawText(QRectF(2, self.height() - fm_h - round(5 * s), self.width() - 4, fm_h), Qt.AlignCenter, txt)
        p.end()


# ====================================================================== клавиши
def draw_glyph(p: QPainter, rect: QRectF, token: str, color: QColor):
    """Векторни символи (стрелки, Enter, Backspace, Win, меню, звук)."""
    cx, cy = rect.center().x(), rect.center().y()
    w = min(rect.width(), rect.height())
    u = w / 10.0
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    if token in ("left", "right", "up", "down", "shift"):
        path = QPainterPath()
        # стрелка, насочена нагоре, после въртим
        path.moveTo(0, -3.6 * u)
        path.lineTo(3 * u, 0)
        path.lineTo(1.2 * u, 0)
        path.lineTo(1.2 * u, 3.4 * u)
        path.lineTo(-1.2 * u, 3.4 * u)
        path.lineTo(-1.2 * u, 0)
        path.lineTo(-3 * u, 0)
        path.closeSubpath()
        ang = {"up": 0, "shift": 0, "right": 90, "down": 180, "left": 270}[token]
        p.save()
        p.translate(cx, cy)
        p.rotate(ang)
        p.drawPath(path)
        p.restore()
    elif token == "enter":
        p.setBrush(Qt.NoBrush)
        pen = QPen(color, max(1.6, u * 0.8), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(cx + 3.4 * u, cy - 3 * u)
        path.lineTo(cx + 3.4 * u, cy + 1.2 * u)
        path.lineTo(cx - 3 * u, cy + 1.2 * u)
        p.drawPath(path)
        p.setBrush(color)
        p.drawPolygon([QPointF(cx - 4.6 * u, cy + 1.2 * u), QPointF(cx - 1.6 * u, cy - 1.4 * u),
                       QPointF(cx - 1.6 * u, cy + 3.8 * u)])
    elif token == "backspace":
        path = QPainterPath()
        path.moveTo(cx - 5 * u, cy)
        path.lineTo(cx - 2.2 * u, cy - 3.4 * u)
        path.lineTo(cx + 5 * u, cy - 3.4 * u)
        path.lineTo(cx + 5 * u, cy + 3.4 * u)
        path.lineTo(cx - 2.2 * u, cy + 3.4 * u)
        path.closeSubpath()
        p.drawPath(path)
        p.setPen(QPen(QColor("#E6E6E6"), max(1.4, u * 0.7), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx - 0.6 * u, cy - 1.5 * u), QPointF(cx + 2.8 * u, cy + 1.5 * u))
        p.drawLine(QPointF(cx - 0.6 * u, cy + 1.5 * u), QPointF(cx + 2.8 * u, cy - 1.5 * u))
    elif token == "win":
        for col in (0, 1):
            for row in (0, 1):
                p.drawRoundedRect(QRectF(cx - 4.2 * u + col * 4.9 * u, cy - 4.2 * u + row * 4.9 * u, 3.5 * u, 3.5 * u),
                                  0.3 * u, 0.3 * u)
    elif token == "menu":
        for dx in (-1, 1):
            for dy in (-1, 1):
                p.drawRoundedRect(QRectF(cx + dx * 2.3 * u - 1.8 * u, cy + dy * 2.3 * u - 1.8 * u, 3.6 * u, 3.6 * u), u * 0.5, u * 0.5)
    elif token in ("voldown", "volup"):
        path = QPainterPath()
        path.moveTo(cx - 4.6 * u, cy - 1.6 * u)
        path.lineTo(cx - 2.4 * u, cy - 1.6 * u)
        path.lineTo(cx + 0.4 * u, cy - 3.8 * u)
        path.lineTo(cx + 0.4 * u, cy + 3.8 * u)
        path.lineTo(cx - 2.4 * u, cy + 1.6 * u)
        path.lineTo(cx - 4.6 * u, cy + 1.6 * u)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(color, max(1.2, u * 0.7), Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - 1.4 * u, cy - 2.2 * u, 4.4 * u, 4.4 * u), -60 * 16, 120 * 16)
        if token == "volup":
            p.drawArc(QRectF(cx - 0.4 * u, cy - 3.8 * u, 7.6 * u, 7.6 * u), -60 * 16, 120 * 16)


GLYPH_TOKENS = {"left", "right", "up", "down", "shift", "enter", "backspace", "win", "menu", "voldown", "volup"}
TEXT_FOR = {"ctrl": "Ctrl", "alt": "Alt", "esc": "Esc", "fn": "Fn", "altgr": "AltGr", "space": "", "tab": "Tab",
            "delete": "Del", "plus": "+", "minus": "–", "mute": "Mute", "home": "Home", "end": "End",
            "prtsc": "PrtSc", "caps": "Caps"}


def draw_keycap(p: QPainter, rect: QRectF, token: str, theme, s: float, hover=False, down=False):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, rect.top(), 0, rect.bottom())
    top, bot = QColor(theme.keycap_top), QColor(theme.keycap_bottom)
    if hover:
        top, bot = QColor("#EAF1FF"), QColor("#BFD3F5")
    if down:
        top, bot = bot, top.darker(110)
    g.setColorAt(0, top)
    g.setColorAt(1, bot)
    p.setPen(QPen(QColor(theme.keycap_border), 1.4))
    p.setBrush(g)
    p.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 4 * s, 4 * s)
    p.setPen(QPen(QColor(255, 255, 255, 140), 1))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 3 * s, 3 * s)
    col = QColor(theme.keycap_text)
    key = token.lower()
    if key in GLYPH_TOKENS:
        draw_glyph(p, rect.adjusted(0, 0, 0, 0), key, col)
    else:
        text = TEXT_FOR.get(key, token if len(token) > 1 else token.upper())
        if text:
            p.setPen(col)
            p.setFont(font(min(13 * s, rect.height() * 0.5), QFont.DemiBold))
            p.drawText(rect, Qt.AlignCenter, text)
    p.restore()


class KeyCap(QWidget):
    """Самостоятелен виртуален клавиш (десния панел на клавиатурата)."""
    clicked = Signal()

    def __init__(self, theme, s, token, tooltip="", parent=None, enabled_look=True):
        super().__init__(parent)
        self.theme, self.s, self.token = theme, s, token
        self._hover = self._down = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if tooltip:
            self.setToolTip(tooltip)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = self._down = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._down:
            self._down = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        draw_keycap(p, QRectF(self.rect()), self.token, self.theme, self.s, self._hover, self._down)
        p.end()


class ComboButton(QWidget):
    """Клавишна комбинация „Shift + Win + S“: един клик изпраща цялата комбинация."""
    clicked = Signal()

    def __init__(self, theme, s, tokens, tooltip="", parent=None):
        super().__init__(parent)
        self.theme, self.s, self.tokens = theme, s, tokens
        self.key_w, self.key_h, self.plus_w, self.wide = self.metrics(s)
        self._hover = self._down = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.total_width() + round(8 * s), self.key_h + round(8 * s))
        if tooltip:
            self.setToolTip(tooltip)

    @staticmethod
    def metrics(s):
        return round(30 * s), round(29 * s), round(12 * s), {"ctrl": round(40 * s), "alt": round(34 * s)}

    @staticmethod
    def natural_width(tokens, s):
        kw, _, pw, wide = ComboButton.metrics(s)
        return sum(wide.get(t.lower(), kw) for t in tokens) + pw * (len(tokens) - 1) + round(8 * s)

    def kw(self, tok):
        return self.wide.get(tok.lower(), self.key_w)

    def total_width(self):
        return sum(self.kw(t) for t in self.tokens) + self.plus_w * (len(self.tokens) - 1)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = self._down = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._down:
            self._down = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t, s = self.theme, self.s
        if self._hover:
            p.setPen(QPen(QColor(t.active_border), 1.2))
            p.setBrush(QColor(t.active_top).darker(300) if t.name == "dark" else QColor(t.tile_hover))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6 * s, 6 * s)
        x = (self.width() - self.total_width()) / 2
        y = (self.height() - self.key_h) / 2
        for i, tok in enumerate(self.tokens):
            w = self.kw(tok)
            draw_keycap(p, QRectF(x, y, w, self.key_h), tok, t, s, self._hover, self._down)
            x += w
            if i < len(self.tokens) - 1:
                p.setPen(QColor(t.text))
                p.setFont(font(17 * s))
                p.drawText(QRectF(x, y - 1, self.plus_w, self.key_h), Qt.AlignCenter, "+")
                x += self.plus_w
        p.end()
