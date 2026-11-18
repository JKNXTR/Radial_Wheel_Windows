"""Главният прозорец: колело + горен панел. Позициониране, показване/скриване, превключване на панелите."""
import logging
import os
import sys
import time
from contextlib import contextmanager

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget

from . import icons, winapi
from .actions import Actions
from .config import SECTOR_IDS, cfg
from .layout import GRID_PANELS, grid_params, panel_count
from .paths import SOUNDS
from .panels import BUILDERS, Ctx
from .widgets import Frame
from .theme import build_theme
from .wheel import CENTER, NONE, WheelWidget

log = logging.getLogger(__name__)

BASE_D = 280          # диаметър на колелото при мащаб 100 %
PANEL_RATIO = 3.0     # ширина на панела ≈ 2.5–3 × диаметъра (спец. 2.2)
PANEL_H = 124
# коя страница от настройките отваря зъбното колело във всеки панел
PANEL_SETTINGS_PAGE = {"keyboard": "shortcuts", "folders": "folders", "programs": "programs", "favorites": "favorites",
                       "internet": "internet", "system": "functions", "sound": "sounds"}


def play_tick():
    if sys.platform == "win32" and cfg["sounds"]:
        try:
            import winsound
            winsound.PlaySound(str(SOUNDS / "tick.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            log.exception("Звукът не може да се възпроизведе")


class Catcher(QWidget):
    """Почти прозрачен слой върху екрана: хваща кликовете „извън“ колелото (Two-Step Dismiss)."""

    def __init__(self, on_click):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
                         | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._on_click = on_click

    def paintEvent(self, _):
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))      # alpha=1: невидим, но прихваща мишката
        p.end()

    def mousePressEvent(self, e):
        self._on_click()


class Overlay(QWidget):
    def __init__(self, controller):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.controller = controller
        self.act = Actions(controller)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.focus_widget = None
        self.panel = None
        self.panel_sid = None
        self.wheel = None
        self.zone = QWidget(self)
        self.zone.setAttribute(Qt.WA_TranslucentBackground)
        self._modal = 0
        self.pinned = False
        self.catcher = Catcher(self.outside_click)
        self._prev_hwnd = 0
        self._shown_at = 0.0
        self._left_at = None
        self._wheel_center = QPoint()
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setDuration(110)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._watch = QTimer(self)
        self._watch.setInterval(150)
        self._watch.timeout.connect(self._watchdog)
        QGuiApplication.instance().applicationStateChanged.connect(self._on_app_state)
        self.rebuild()

    # ------------------------------------------------------------ размери
    def _metrics(self, s):
        """Всички размери при мащаб s. Панелите могат да са различни; зоната е по най-големия."""
        a = cfg["appearance"]
        ps = s * a["panel_scale"]
        sh = round(6 * ps)
        dims = {}
        for sid in SECTOR_IDS:
            if sid in GRID_PANELS:
                gp = grid_params(sid, panel_count(sid), ps)
                dims[sid] = (gp["W"], gp["H"])
            else:                                               # клавиатура / интернет / звук – фиксирани панели
                dims[sid] = (round(BASE_D * PANEL_RATIO * ps) + 2 * sh, round(PANEL_H * ps) + 2 * sh)
        m = dict(s=s, ps=ps, D=round(BASE_D * s), dims=dims, zone_w=max(w for w, _ in dims.values()),
                 zone_h=max(h for _, h in dims.values()), gap=round(30 * s), margin=round(6 * s))
        m["pad"] = max(10, int(m["D"] * 0.05))
        wheel = m["D"] + 2 * m["pad"]
        m["W"] = m["zone_w"] + 2 * m["margin"]
        m["wy"] = m["margin"] + m["zone_h"] + m["gap"] - m["pad"]
        m["H"] = m["wy"] + wheel + m["margin"]
        m["wx"] = (m["W"] - wheel) // 2
        return m

    def _fit_scale(self, screen) -> float:
        s = cfg["appearance"]["scale"]
        geo = screen.availableGeometry() if screen else QGuiApplication.primaryScreen().availableGeometry()
        while s > 0.45:
            m = self._metrics(s)
            if m["W"] <= geo.width() - 20 and m["H"] <= geo.height() - 20:
                break
            s -= 0.03
        return max(0.45, s)

    def rebuild(self, screen=None):
        """(Пре)изгражда колелото според текущата конфигурация и мащаб."""
        a = cfg["appearance"]
        self.s = self._fit_scale(screen)
        m = self._metrics(self.s)
        s = self.s
        self.theme = build_theme(a["theme"], a["accent"])
        self.D, self.dims = m["D"], m["dims"]
        self.zone_w, self.zone_h = m["zone_w"], m["zone_h"]
        if self.wheel:
            self.wheel.deleteLater()
        sector_icons = []
        for sid in cfg["sector_order"]:
            custom = cfg["custom_icons"].get(sid, "")
            sector_icons.append(custom if custom and os.path.exists(os.path.expandvars(custom)) else icons.builtin("sector_" + {
                "keyboard": "keyboard", "folders": "folders", "system": "windows", "favorites": "favorites",
                "sound": "sound", "internet": "internet", "settings": "settings", "programs": "programs"}[sid]))
        self.wheel = WheelWidget(self.theme, self.D, sector_icons, self)
        self.wheel.hover_delay = cfg["behavior"]["hover_delay_ms"]
        self.wheel.hovered.connect(self._on_hovered)
        self.wheel.sectorClicked.connect(self._on_sector_clicked)
        self.wheel.centerClicked.connect(self.press_delete)
        self.wheel.rightClicked.connect(self.outside_click)
        self.wheel.outsideClicked.connect(self.outside_click)
        self.setFixedSize(m["W"], m["H"])
        self.zone.setGeometry(m["margin"], m["margin"], self.zone_w, self.zone_h)
        self.wheel.move(m["wx"], m["wy"])
        self.wheel.show()
        self._wheel_center = QPoint(m["wx"] + self.wheel.width() // 2, m["wy"] + self.wheel.height() // 2)
        self.ctx = Ctx(self.theme, m["ps"], self.act, self)
        self._clear_panel()

    def press_delete(self):
        """Централният бутон Delete работи като клавиша Delete: скрива колелото и го праща към предишния прозорец."""
        self.act.keys("Delete")

    # ------------------------------------------------------------ показване
    def popup(self):
        if self.isVisible():
            self.close_menu(True)
            return
        pos = QCursor.pos()
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if abs(self._fit_scale(screen) - self.s) > 0.005:
            self.rebuild(screen)
        self.wheel.reset_state()
        self._clear_panel()
        geo = screen.availableGeometry()
        x = pos.x() - self._wheel_center.x()
        y = pos.y() - self._wheel_center.y()
        nx = min(max(x, geo.left()), geo.right() - self.width() + 1)
        ny = min(max(y, geo.top()), geo.bottom() - self.height() + 1)
        if (nx, ny) != (x, y):                         # колелото не се събира около курсора -> местим и курсора
            QCursor.setPos(nx + self._wheel_center.x(), ny + self._wheel_center.y())
        self.move(nx, ny)
        self._prev_hwnd = winapi.get_foreground()
        op = cfg["appearance"]["opacity"]
        if cfg["appearance"]["animations"]:
            self.setWindowOpacity(0.0)
        else:
            self.setWindowOpacity(op)
        self.catcher.setGeometry(screen.geometry())
        self.catcher.show()
        self.show()
        self.raise_()
        winapi.force_foreground(int(self.winId()))
        self.activateWindow()
        self.setFocus()
        if cfg["appearance"]["animations"]:
            self._anim.stop()
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(op)
            self._anim.start()
        self._shown_at = time.monotonic()
        self._left_at = None
        self._watch.start()

    def close_menu(self, restore=True):
        if not self.isVisible():
            return
        self._watch.stop()
        self._anim.stop()
        self.catcher.hide()
        self.hide()
        self.wheel.reset_state()
        self._clear_panel()
        if restore:
            winapi.restore_foreground(self._prev_hwnd)

    # ------------------------------------------------------------ панели
    def _clear_panel(self):
        if self.panel is not None:
            self.panel.hide()
            self.panel.deleteLater()
        self.panel = None
        self.panel_sid = None
        self.focus_widget = None
        self.pinned = False

    def show_panel(self, sid):
        if sid == self.panel_sid and self.panel is not None:
            return
        self._clear_panel()
        try:
            pw, ph = self.dims[sid]
            w = BUILDERS[sid](self.ctx, pw, ph)
        except Exception:
            log.exception("Грешка при изграждане на панел %s", sid)
            return
        w.setParent(self.zone)
        w.move((self.zone_w - w.width()) // 2, 0)
        w.show()
        self.panel, self.panel_sid = w, sid
        frames = ([w] if isinstance(w, Frame) else []) + w.findChildren(Frame)
        for fr in frames:
            fr.closeRequested.connect(self.close_panel)
        page = PANEL_SETTINGS_PAGE.get(sid)
        glob = [f for f in frames if f.has_close]
        if page and glob:
            glob[0].has_gear = True
            glob[0].settingsRequested.connect(lambda p=page: self.act.open_settings(p))
        if self.focus_widget is not None:
            fw = self.focus_widget
            QTimer.singleShot(0, lambda: (self.activateWindow(), fw.setFocus(Qt.OtherFocusReason)))

    def refresh_panel(self):
        sid = self.panel_sid
        self._clear_panel()
        if sid and self.isVisible():
            self.show_panel(sid)

    def _on_hovered(self, idx):
        if idx >= 0:
            play_tick()
        if self.pinned:
            return
        if idx == CENTER or idx == NONE:
            self._clear_panel()
        elif cfg["behavior"]["open_mode"] == "hover":
            self.show_panel(cfg["sector_order"][idx])

    def _on_sector_clicked(self, idx):
        """Click-to-Pin: клик върху сектора фиксира неговия панел, докато не бъде затворен."""
        self.show_panel(cfg["sector_order"][idx])
        if self.panel is not None:
            self.pinned = True
            self.wheel.locked = True

    def close_panel(self):
        """Затваря само горния панел; колелото остава в изходно състояние."""
        self._clear_panel()
        self.wheel.reset_state()
        self.wheel._armed = True

    def outside_click(self, *_):
        """Two-Step Dismiss: 1-ви клик извън панела го затваря, 2-ри клик извън колелото скрива всичко."""
        if self.panel is not None:
            self.close_panel()
        else:
            self.close_menu(True)

    # ------------------------------------------------------------ модални диалози
    @contextmanager
    def modal(self):
        self._modal += 1
        try:
            yield
        finally:
            self._modal -= 1
            self._shown_at = time.monotonic()

    # ------------------------------------------------------------ автоматично скриване
    def _on_app_state(self, state):
        if (state != Qt.ApplicationActive and self.isVisible() and self._modal == 0
                and time.monotonic() - self._shown_at > 0.4 and not winapi.IS_WIN):      # под Windows това прави _watchdog
            self.close_menu(False)

    def _watchdog(self):
        if self._modal or time.monotonic() - self._shown_at < 0.6:
            return
        # Windows: фокусът е преминал към друг процес (клик извън колелото, Alt+Tab …)
        if winapi.IS_WIN:
            pid = winapi.foreground_pid()
            if pid and pid != os.getpid():
                self.close_menu(False)
                return
        ms = cfg["behavior"]["autohide_ms"]
        if ms > 0:
            if self.geometry().contains(QCursor.pos()):
                self._left_at = None
            else:
                self._left_at = self._left_at or time.monotonic()
                if (time.monotonic() - self._left_at) * 1000 >= ms:
                    self.close_menu(True)

    # ------------------------------------------------------------ събития
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close_menu(True)
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if e.button() in (Qt.LeftButton, Qt.RightButton):
            self.outside_click()         # клик върху празно място на прозореца

    def mouseMoveEvent(self, e):
        # движение над празното пространство (между панел и колело) не променя избора
        pass
