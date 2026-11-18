"""Контролер на приложението: tray икона, глобални тригери, единствен екземпляр, настройки."""
import logging
import os
import subprocess
import sys

from PySide6.QtCore import QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import APP_NAME, autostart, icons, lifecycle
from .config import cfg
from .i18n import set_language, tr
from .overlay import Overlay
from .paths import ASSETS, LOG_FILE, data_dir
from .settings_dialog import SettingsDialog
from .triggers import Triggers

log = logging.getLogger(__name__)

GLOBAL_QSS = """
QToolTip { background:#1E1E1E; color:#ECE6D4; border:1px solid #555; padding:3px 6px; font-family:'Segoe UI'; font-size:12px; }
QMenu { background:#2A2A2A; color:#ECE6D4; border:1px solid #555; padding:4px; font-family:'Segoe UI'; }
QMenu::item { padding:5px 22px; border-radius:3px; }
QMenu::item:selected { background:#4A76C5; color:white; }
QMenu::separator { height:1px; background:#555; margin:4px 8px; }
"""


def pipe_name() -> str:
    return f"{APP_NAME}-{os.environ.get('USERNAME') or os.environ.get('USER') or 'user'}"


def notify_running_instance(message: bytes = b"show") -> str:
    """Праща команда на вече работещ екземпляр. Връща "ok" (отговори), "hung" (връзката е приета, но няма
    отговор – екземплярът е увиснал) или "" (няма екземпляр)."""
    sock = QLocalSocket()
    sock.connectToServer(pipe_name())
    if not sock.waitForConnected(300):
        return ""
    sock.write(message)
    sock.flush()
    sock.waitForBytesWritten(300)
    answered = sock.waitForReadyRead(2000) and bytes(sock.readAll()).startswith(b"ok")
    sock.disconnectFromServer()
    return "ok" if answered else "hung"


class Controller(QObject):
    def __init__(self, app, show_now=False):
        super().__init__()
        self.app = app
        cfg.load()
        set_language(cfg["language"])
        app.setStyleSheet(GLOBAL_QSS)
        app.setQuitOnLastWindowClosed(False)
        app.setWindowIcon(QIcon(str(ASSETS / "app.ico")))

        from . import watchdog
        watchdog.start(self)
        from . import resources
        resources.start(self)
        self.overlay = Overlay(self)
        self.settings = None
        lifecycle.stop_listener()                       # ако клавишът е държан от слушателя – поемаме го
        self.triggers = Triggers(app)
        self.triggers.activated.connect(self.show_wheel, Qt.QueuedConnection)   # извън hook callback-а
        ok, msg = self.reload_triggers()

        self._build_tray()

        self.server = QLocalServer(self)
        QLocalServer.removeServer(pipe_name())
        self.server.newConnection.connect(self._on_connection)
        if not self.server.listen(pipe_name()):
            log.error("QLocalServer.listen неуспешно: %s", self.server.errorString())

        hk = cfg["hotkey"]
        combo = "+".join([m for m, k in (("Ctrl", "ctrl"), ("Alt", "alt"), ("Shift", "shift"), ("Win", "win")) if hk[k]] + [hk["key"]])
        if not ok:
            self.notify(tr("app.title"), tr("tray.hotkey_failed", msg))
        elif not show_now:
            self.notify(tr("app.title"), tr("tray.started", combo) if hk["enabled"] else tr("tray.started_nohk"))
        if show_now:
            QTimer.singleShot(150, self.show_wheel)

    # ------------------------------------------------------------ tray
    def _build_tray(self):
        self.tray = QSystemTrayIcon(QIcon(str(ASSETS / "tray.ico")), self)
        self.tray.setToolTip(tr("app.title"))
        menu = QMenu()
        head = menu.addAction(QIcon(str(ASSETS / "tray.ico")), tr("app.title"))
        head.setEnabled(False)
        menu.addSeparator()
        a_show = menu.addAction(tr("tray.show"))
        a_show.triggered.connect(lambda: QTimer.singleShot(150, self.show_wheel))
        a_set = menu.addAction(tr("tray.settings"))
        a_set.triggered.connect(lambda: self.open_settings("view"))
        self.a_auto = QAction(tr("tray.autostart"), menu)
        self.a_auto.setCheckable(True)
        self.a_auto.setChecked(autostart.is_enabled())
        self.a_auto.toggled.connect(self.set_autostart)
        menu.addAction(self.a_auto)
        menu.addSeparator()
        menu.addAction(tr("tray.config")).triggered.connect(lambda: self._open(str(data_dir())))
        menu.addAction(tr("tray.log")).triggered.connect(lambda: self._open(str(LOG_FILE())))
        menu.addSeparator()
        menu.addAction(tr("tray.close")).triggered.connect(self.close_keep_hotkey)
        menu.addAction(tr("tray.exit")).triggered.connect(self.quit)
        self.tray.setContextMenu(menu)
        self._menu = menu
        self.tray.activated.connect(self._on_tray)
        self.tray.show()

    def _on_tray(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            QTimer.singleShot(150, self.show_wheel)

    @staticmethod
    def _open(path):
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def notify(self, title, message):
        log.info("notify: %s", message)
        try:
            self.tray.showMessage(title, message, QSystemTrayIcon.Information, 6000)
        except Exception:
            log.exception("tray.showMessage неуспешно")

    # ------------------------------------------------------------ действия
    def show_wheel(self):
        try:
            self.overlay.popup()
        except Exception:
            log.exception("Грешка при показване на колелото")

    def apply_config(self, clear_icons=True):
        if clear_icons:
            icons.clear_cache()
        self.overlay.close_menu(False)
        self.overlay.rebuild()

    def reload_triggers(self):
        return self.triggers.reload(cfg)

    def set_autostart(self, enabled: bool):
        ok = autostart.set_enabled(enabled)
        self.a_auto.blockSignals(True)
        self.a_auto.setChecked(autostart.is_enabled() if ok else not enabled)
        self.a_auto.blockSignals(False)
        if self.settings is not None and hasattr(self.settings, "_autostart_box"):
            box = self.settings._autostart_box
            box.blockSignals(True)
            box.setChecked(autostart.is_enabled())
            box.blockSignals(False)

    def open_settings(self, page="view"):
        if self.settings is None:
            self.settings = SettingsDialog(self)
        self.settings.open_page(page)

    def _on_connection(self):
        conn = self.server.nextPendingConnection()
        if conn is None:
            return

        def read():
            data = bytes(conn.readAll())
            conn.write(b"ok")                    # потвърждение: екземплярът е жив
            conn.flush()
            conn.disconnectFromServer()
            if data.startswith(b"show"):
                QTimer.singleShot(100, self.show_wheel)
        conn.readyRead.connect(read)

    def close_keep_hotkey(self):
        """Затваря приложението, но оставя лек слушател – клавишната комбинация го стартира отново."""
        self.triggers.shutdown()
        try:
            if cfg["hotkey"]["enabled"]:
                lifecycle.spawn_listener()
        except Exception:
            log.exception("Слушателят не може да се стартира")
        self.tray.hide()
        self.server.close()
        self.app.quit()

    def apply_update(self, staged):
        """Стартира помощник, затваря всичко (и слушателя) и оставя помощника да подмени файловете."""
        from . import updater
        updater.launch_helper(staged)
        try:
            lifecycle.stop_listener()
        except Exception:
            log.exception("Слушателят не може да се спре")
        self.quit()

    def quit(self):
        """Изход напълно: без слушател; клавишът не работи до следващото стартиране / вход в Windows."""
        self.triggers.shutdown()
        self.tray.hide()
        self.server.close()
        self.app.quit()
