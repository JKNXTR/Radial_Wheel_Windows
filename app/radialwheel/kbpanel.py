"""Панел „Клавиатура“: три компактни панела; при посочване един се разгъва (плавно), а другите избледняват.

* Бързи комбинации  -> решетка с големи бутони за комбинации
* Стандартна клавиатура -> компактна клавиатура (15 × 5 единици, квадратни клавиши) на текущия език
* Основни клавиши -> големи клавиши Enter/Space/Backspace/Win/..., Vol, Esc, Tab, Delete ...
"""
import logging

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QRectF, QTimer, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from . import winapi
from .config import cfg
from .i18n import tr
from .layout import PANEL_H, kbd_dims
from .widgets import ComboButton, Frame, KeyCap, Tile, draw_keycap, font
from . import icons

log = logging.getLogger(__name__)

# редове на компактната клавиатура: (етикет/vk, ширина в единици, вид)
#   вид: "k" = клавиш с етикет от подредбата, "m" = модификатор (залепва), "x" = функционален (токен), "v" = символ
def _rows():
    top = [("`", 0xC0), *[(c, ord(c)) for c in "1234567890"], ("-", 0xBD), ("=", 0xBB)]
    r1 = [(("k", v), 1) for _, v in top] + [(("x", "backspace", 0x08), 2)]
    r2 = [(("x", "tab", 0x09), 1.5)] + [(("k", ord(c)), 1) for c in "QWERTYUIOP"] + [(("k", 0xDB), 1), (("k", 0xDD), 1), (("k", 0xDC), 1.5)]
    r3 = [(("x", "caps", 0x14), 1.75)] + [(("k", ord(c)), 1) for c in "ASDFGHJKL"] + [(("k", 0xBA), 1), (("k", 0xDE), 1), (("x", "enter", 0x0D), 2.25)]
    r4 = [(("m", "shift", 0xA0), 2.25)] + [(("k", ord(c)), 1) for c in "ZXCVBNM"] + [(("k", 0xBC), 1), (("k", 0xBE), 1), (("k", 0xBF), 1), (("m", "shift", 0xA1), 2.75)]
    r5 = [(("m", "ctrl", 0xA2), 1.25), (("m", "win", 0x5B), 1.25), (("m", "alt", 0xA4), 1.25), (("x", "space", 0x20), 6.25),
          (("m", "alt", 0xA5), 1.25), (("m", "ctrl", 0xA3), 1.25), (("x", "left", 0x25), 1.25), (("x", "right", 0x27), 1.25)]
    return [r1, r2, r3, r4, r5]


class OskKey(QWidget):
    """Клавиш на компактната клавиатура."""

    def __init__(self, theme, s, token, sub, vk, kind, on_click):
        super().__init__()
        self.theme, self.s, self.token, self.sub, self.vk, self.kind, self.on_click = theme, s, token, sub, vk, kind, on_click
        self.latched = False
        self._hover = self._down = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

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
                self.on_click(self)

    def paintEvent(self, _):
        p = QPainter(self)
        r = QRectF(self.rect())
        draw_keycap(p, r, self.token, self.theme, self.s * 1.3, self._hover, self._down or self.latched)
        if self.latched:
            p.setPen(QPen(QColor(self.theme.active_border), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), 5 * self.s, 5 * self.s)
        if self.sub:
            p.setPen(QColor(self.theme.keycap_text).lighter(150))
            p.setFont(font(max(8.0, r.height() * 0.22)))
            p.drawText(r.adjusted(0, r.height() * 0.06, -r.width() * 0.1, 0), Qt.AlignTop | Qt.AlignRight, self.sub)
        p.end()


class KeyboardPanel(QWidget):
    def __init__(self, ctx, W, H):
        super().__init__()
        self.ctx = ctx
        s, th = ctx.s, ctx.theme
        self.s = s
        self.setFixedSize(W, H)
        self.sh = sh = round(6 * s)
        gap = round(14 * s)
        kd = kbd_dims(s, W)
        self.Hc = kd["Hc"]
        vis = (W - 2 * sh - 2 * gap) / 3.0
        widths = [round(vis * 1.25), round(vis * 0.72), round(vis * 1.03)]
        titles = ("panel.quick_keys", "panel.std_keyboard", "panel.win_keys")
        self.frames, self.compact, self.big, self.rects = [], [], [], []
        x = 0
        self.fx_op = []
        for i, key in enumerate(titles):
            f = Frame(th, s, tr(key), "global", self)
            rect = (x, H - self.Hc, widths[i] + 2 * sh, self.Hc)
            f.setGeometry(*rect)
            self.frames.append(f)
            self.rects.append(rect)
            x += widths[i] + gap
            f.installEventFilter(self)
        self.full = (0, 0, W, H)
        # компактно съдържание
        self.compact = [self._compact_combos(widths[0]), self._compact_mid(), self._compact_right()]
        # разгънато съдържание (изгражда се при първо разгъване – клавиатурата зависи от текущия език)
        self.big = [None, None, None]
        self._built = [False] * 3
        self.cur = -1
        self.t = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.anim.valueChanged.connect(self._apply)
        self.anim.finished.connect(self._finished)
        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.timeout.connect(self._start_expand)
        self._want = -1
        self._watch = QTimer(self)
        self._watch.setInterval(120)
        self._watch.timeout.connect(self._check_leave)
        self._outside = 0
        self.latched = {}
        for i, f in enumerate(self.frames):
            self._place_compact(i)

    # ------------------------------------------------------------ компактни съдържания
    def _body(self, f):
        return f.content

    def _place_compact(self, i):
        f = self.frames[i]
        c = self.compact[i]
        c.setParent(f.content)
        f.layout_.addWidget(c)             # заема цялото тяло на кадъра; при разгъване се скрива с избледняване

    def _compact_combos(self, w0):
        s, th, ctx = self.s, self.ctx.theme, self.ctx
        cont = QWidget()
        box = QVBoxLayout(cont)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(round(4 * s))
        avail = w0 - 2 * round(8 * s) - round(4 * s)
        for row in cfg["quick_shortcuts"]:
            items = [(it, [k for k in it["keys"].replace(" ", "").split("+") if k]) for it in row]
            need = sum(ComboButton.natural_width(tk, s) for _, tk in items) + round(5 * s) * (len(items) + 1)
            f = min(1.0, avail / need) if need else 1.0
            hl = QHBoxLayout()
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(round(4 * s))
            hl.addStretch(1)
            for item, tokens in items:
                btn = ComboButton(th, s * f, tokens, self._tip(item))
                btn.clicked.connect(lambda c=item["keys"]: ctx.act.keys(c))
                hl.addWidget(btn)
                hl.addStretch(1)
            box.addLayout(hl, 1)
        return cont

    @staticmethod
    def _tip(item):
        tip = tr("tip." + item.get("tip", ""))
        if not item.get("tip") or tip == "tip." + item.get("tip", ""):
            tip = item.get("tip") or item["keys"]
        return tip

    def _compact_mid(self):
        ctx, s, th = self.ctx, self.s, self.ctx.theme
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        t = Tile(th, s, "", icons.builtin("kb_keyboard"), tr("tip.osk"), icon_ratio=0.9)
        t.clicked.connect(ctx.act.osk)
        lay.addStretch(1)
        lay.addWidget(t, 3)
        lay.addStretch(1)
        return cont

    def _special_keys(self):
        """Клавиши на десния панел: (токен, комбинация, подсказка, затваря ли, индикативен)."""
        return [
            [("enter", "Enter", "tip.enter", True, False), ("space", "Space", "tip.space", True, False),
             ("backspace", "Backspace", "tip.backspace", True, False)],
            [("win", "Win", "tip.win", True, False), ("menu", "Apps", "tip.menu", True, False),
             ("esc", "Esc", "tip.esc", True, False), ("tab", "Tab", "", True, False),
             ("delete", "Delete", "", True, False), ("fn", "", "tip.fn", True, True), ("altgr", "AltGr", "tip.altgr", True, False)],
            [("voldown", "VolDown", "tip.voldown", False, False), ("volup", "VolUp", "tip.volup", False, False),
             ("mute", "Mute", "", False, False), ("home", "Home", "", True, False), ("end", "End", "", True, False),
             ("prtsc", "PrintScreen", "", True, False)],
        ]

    def _compact_right(self):
        ctx, s, th = self.ctx, self.s, self.ctx.theme
        cont = QWidget()
        col = QVBoxLayout(cont)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(round(6 * s))
        rows = self._special_keys()
        r1 = QHBoxLayout()
        r1.setSpacing(round(8 * s))
        for (tok, combo, tip, close, noop), wt in zip(rows[0], (2, 6, 2)):
            r1.addWidget(self._cap(tok, combo, tip, close, noop), wt)
        r2 = QHBoxLayout()
        r2.setSpacing(round(5 * s))
        compact_row = [("win", "Win", "tip.win", True, False, 14), ("menu", "Apps", "tip.menu", True, False, 12),
                       ("voldown", "VolDown", "tip.voldown", False, False, 12), ("volup", "VolUp", "tip.volup", False, False, 12),
                       ("esc", "Esc", "tip.esc", True, False, 13), ("fn", "", "tip.fn", True, True, 12),
                       ("altgr", "AltGr", "tip.altgr", True, False, 14)]
        for tok, combo, tip, close, noop, wt in compact_row:
            r2.addWidget(self._cap(tok, combo, tip, close, noop), wt)
        col.addLayout(r1, 1)
        col.addLayout(r2, 1)
        return cont

    def _cap(self, tok, combo, tip, close, noop):
        k = KeyCap(self.ctx.theme, self.s, tok, tr(tip) if tip else "")
        if not noop:
            k.clicked.connect(lambda: self.ctx.act.keys(combo, close=close))
        return k

    # ------------------------------------------------------------ разгънато съдържание
    def _build_big(self, i):
        f = self.frames[i]
        W, H = self.full[2], self.full[3]
        sh, pad, hd = self.sh, round(8 * self.s), f.header_h
        bw, bh = W - 2 * (sh + pad), H - 2 * sh - hd - 2 * pad
        w = QWidget(f.content)
        w.setGeometry(0, 0, bw, bh)
        if i == 0:
            self._big_combos(w, bw, bh)
        elif i == 1:
            self._big_keyboard(w, bw, bh)
        else:
            self._big_special(w, bw, bh)
        w.hide()
        self.big[i] = w
        self._built[i] = True

    def _big_combos(self, w, bw, bh):
        s, th, ctx = self.s, self.ctx.theme, self.ctx
        rows = cfg["quick_shortcuts"] or [[]]
        ncol = max(1, max(len(r) for r in rows))
        cw, ch = bw / ncol, bh / len(rows)
        need = max((ComboButton.natural_width([k for k in it["keys"].replace(" ", "").split("+") if k], 1.0)
                    for r in rows for it in r), default=60)
        factor = max(1.0, min(2.6, (cw * 0.92) / need, (ch * 0.8) / (37.0)))      # 37 = высота на комбинация при s=1
        for r, row in enumerate(rows):
            for c, it in enumerate(row):
                btn = ComboButton(th, factor, [k for k in it["keys"].replace(" ", "").split("+") if k], self._tip(it), w)
                btn.clicked.connect(lambda cmb=it["keys"]: ctx.act.keys(cmb))
                btn.move(int(c * cw + (cw - btn.width()) / 2), int(r * ch + (ch - btn.height()) / 2))

    def _big_special(self, w, bw, bh):
        s, th, ctx = self.s, self.ctx.theme, self.ctx
        rows = self._special_keys()
        wts = [(2, 6, 2), None, None]
        ch = bh / len(rows)
        gap = round(6 * s)
        for r, row in enumerate(rows):
            weights = wts[r] or tuple(1 for _ in row)
            total = float(sum(weights))
            x = 0.0
            for (tok, combo, tip, close, noop), wt in zip(row, weights):
                cw = bw * wt / total
                k = KeyCap(th, s * 1.6, tok, tr(tip) if tip else "", w)
                k.setGeometry(int(x + gap / 2), int(r * ch + gap / 2), int(cw - gap), int(ch - gap))
                if not noop:
                    k.clicked.connect(lambda cmb=combo, cl=close: ctx.act.keys(cmb, close=cl))
                x += cw

    def _big_keyboard(self, w, bw, bh):
        ctx, s, th = self.ctx, self.s, self.ctx.theme
        prev = getattr(ctx.overlay, "_prev_hwnd", 0)
        lang, labels = winapi.keyboard_labels(prev)
        self.frames[1].title = f"{tr('panel.std_keyboard')} · {lang}"
        self.frames[1].update()
        u = bw / 15.0
        uh = bh / 5.0
        gap = max(2.0, round(3 * s))
        self.mods = {}
        self.osk_keys = []
        for r, row in enumerate(_rows()):
            x = 0.0
            for spec, wu in row:
                kind = spec[0]
                if kind == "k":
                    vk = spec[1]
                    base, shifted = labels.get(vk, ("?", "?"))
                    token, sub = base.upper() if len(base) == 1 and base.isalpha() else base, (shifted if not base.isalpha() else "")
                elif kind in ("x", "m"):
                    token, vk, sub = spec[1], spec[2], ""
                key = OskKey(th, s, token, sub, vk, kind, self._osk_click)
                key.setParent(w)
                key.setGeometry(int(x * u + gap / 2), int(r * uh + gap / 2), int(wu * u - gap), int(uh - gap))
                key.show()
                self.osk_keys.append(key)
                x += wu

    def _osk_click(self, key):
        if key.kind == "m":
            key.latched = not key.latched
            key.update()
            return
        mods = [k.vk for k in self.osk_keys if k.kind == "m" and k.latched]
        self.ctx.act.type_keys(mods + [key.vk])
        for k in self.osk_keys:
            if k.kind == "m" and k.latched:
                k.latched = False
                k.update()

    # ------------------------------------------------------------ анимация
    @staticmethod
    def _set_opacity(w, v):
        eff = w.graphicsEffect()
        if eff is None:
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
        eff.setOpacity(max(0.0, min(1.0, v)))

    @staticmethod
    def _no_effect(w):
        if w is not None and w.graphicsEffect() is not None:
            w.setGraphicsEffect(None)

    def _prepare_effects(self, i):
        """Ефектите на прозрачност никога не се влагат: разгънатият кадър ги има само по съдържанието си,
        останалите – само по кадъра (вложени ефекти дават грешки при рисуване)."""
        for k, f in enumerate(self.frames):
            if k == i:
                self._no_effect(f)
                self._set_opacity(self.compact[k], 1.0)
                self._set_opacity(self.big[k], 0.0)
            else:
                self._no_effect(self.compact[k])
                self._no_effect(self.big[k])
                self._set_opacity(f, 1.0)

    def _clear_effects(self):
        for k, f in enumerate(self.frames):
            self._no_effect(f)
            self._no_effect(self.compact[k])
            self._no_effect(self.big[k])

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Enter and obj in self.frames:
            i = self.frames.index(obj)
            if i != self.cur or self.t < 0.99:
                self._want = i
                if self.t < 0.05 or self.cur == i:
                    self._pending.start(130)          # кратко забавяне, за да не се разгъва при преминаване
        elif ev.type() == QEvent.Leave and obj in self.frames and self._pending.isActive():
            self._pending.stop()
        return False

    def expand(self, i):
        self._want = i
        self._start_expand()

    def _start_expand(self):
        i = self._want
        if i < 0:
            return
        if not self._built[i]:
            self._build_big(i)
        if self.cur != -1 and self.cur != i:
            return                                  # първо се връща в нормално състояние
        if self.cur != i:
            self.cur = i
            self._prepare_effects(i)
            self.frames[i].raise_()
            self.big[i].show()
        self._run(1.0)
        self._outside = 0
        self._watch.start()

    def collapse(self):
        self._run(0.0)

    def _run(self, end):
        self.anim.stop()
        self.anim.setStartValue(float(self.t))
        self.anim.setEndValue(float(end))
        self.anim.setDuration(max(80, int(300 * abs(end - self.t))))
        self.anim.start()

    def _lerp(self, a, b, t):
        return tuple(round(x + (y - x) * t) for x, y in zip(a, b))

    def _apply(self, t):
        t = float(t)
        self.t = t
        i = self.cur
        if i < 0:
            return
        for k, f in enumerate(self.frames):
            if k == i:
                f.setGeometry(*self._lerp(self.rects[k], self.full, t))
                self._set_opacity(self.compact[k], 1.0 - min(1.0, t * 1.7))
                self._set_opacity(self.big[k], (t - 0.3) / 0.7)
                self.compact[k].setVisible(t < 0.6)
            else:
                self._set_opacity(f, 1.0 - min(1.0, t * 1.25))
                f.setAttribute(Qt.WA_TransparentForMouseEvents, t > 0.5)

    def _finished(self):
        if self.t <= 0.001:
            self._watch.stop()
            if 0 <= self.cur < 3 and self.big[self.cur] is not None:
                self.big[self.cur].hide()
                self.compact[self.cur].show()
            for f in self.frames:
                f.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._clear_effects()
            self.cur = -1

    def _check_leave(self):
        inside = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        self._outside = 0 if inside else self._outside + 1
        if self._outside >= 2 and self.t > 0 and self.anim.endValue() != 0.0:
            self.collapse()


def build_keyboard(ctx, W, H):
    return KeyboardPanel(ctx, W, H)
