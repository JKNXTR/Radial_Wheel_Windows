"""Изпълнение на действията от панелите: клавишни комбинации, стартиране, папки, системни команди."""
import logging
import os
import subprocess
import sys
from urllib.parse import quote_plus

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from . import winapi
from .config import cfg
from .i18n import tr

log = logging.getLogger(__name__)

# Цели за стартиране по подразбиране (пробват се последователно). "shell:AppsFolder\\..." = UWP приложение.
DEFAULT_PROGRAMS = {
    "browser": ["https://www.google.com"],
    "editor": ["notepad.exe"],
    "player": ["wmplayer.exe", "shell:AppsFolder\\Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic"],
    "calculator": ["calc.exe"],
    "graphics": ["mspaint.exe"],
    "mail": ["mailto:"],
    "games": ["xbox:", "ms-windows-store://home"],
    "notes": ["shell:AppsFolder\\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App", "notepad.exe"],
}

_PF = os.environ.get("ProgramFiles", r"C:\Program Files")
_PF86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
_LA = os.environ.get("LOCALAPPDATA", "")
BROWSER_CANDIDATES = {
    "chrome": ["chrome.exe", rf"{_PF}\Google\Chrome\Application\chrome.exe", rf"{_PF86}\Google\Chrome\Application\chrome.exe",
               rf"{_LA}\Google\Chrome\Application\chrome.exe"],
    "firefox": ["firefox.exe", rf"{_PF}\Mozilla Firefox\firefox.exe", rf"{_PF86}\Mozilla Firefox\firefox.exe"],
    "edge": ["msedge.exe", rf"{_PF86}\Microsoft\Edge\Application\msedge.exe", rf"{_PF}\Microsoft\Edge\Application\msedge.exe"],
    "opera": ["opera.exe", rf"{_LA}\Programs\Opera\opera.exe", rf"{_LA}\Programs\Opera GX\opera.exe",
              rf"{_PF}\Opera\opera.exe"],
}

SYSTEM_ACTIONS = ["start", "taskmgr", "settings", "lock", "sleep", "restart", "shutdown", "run"]


def expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def existing_browser_path(bid: str) -> str:
    """Път до инсталиран браузър (за системната му икона) или ''."""
    for c in BROWSER_CANDIDATES.get(bid, []):
        if os.path.isabs(c) and os.path.exists(c):
            return c
    return ""


def start_target(target: str):
    """Стартира exe / файл / URI / UWP приложение. Хвърля изключение при неуспех."""
    target = expand(target)
    if sys.platform != "win32":
        if not QDesktopServices.openUrl(QUrl.fromUserInput(target)):
            raise OSError(f"Не може да се отвори: {target}")
        return
    if target.lower().startswith("shell:appsfolder"):
        subprocess.Popen(["explorer.exe", target])
        return
    os.startfile(target)  # noqa: S606  (ShellExecute – разбира exe, lnk, URL, папки, App Paths)


class Actions:
    def __init__(self, controller):
        self.c = controller          # Controller: .overlay, .notify(), .open_settings()

    # ------------------------------------------------------------ помощни
    @property
    def overlay(self):
        return self.c.overlay

    def after_close(self, fn, delay=110):
        """Скрива колелото, връща фокуса на предишния прозорец и чак тогава изпълнява действието."""
        self.overlay.close_menu(restore=True)
        QTimer.singleShot(delay, lambda: self._safe(fn))

    def _safe(self, fn):
        try:
            fn()
        except Exception as exc:
            log.exception("Действието е неуспешно")
            self.c.notify(tr("app.title"), tr("err.launch", getattr(fn, "__name__", "action"), exc))

    # ------------------------------------------------------------ клавиатура
    def keys(self, combo: str, close=True):
        if close:
            self.after_close(lambda: winapi.send_combo(combo))
        else:
            self._safe(lambda: winapi.send_combo(combo))

    def osk(self):
        def run():
            if sys.platform == "win32":
                os.startfile("osk.exe")
            else:
                raise OSError("Екранната клавиатура е налична само под Windows")
        self.after_close(run)

    # ------------------------------------------------------------ папки / програми / сайтове
    def open_slot(self, key: str, idx: int):
        {"folders": self.open_folder, "programs": self.launch_program, "favorites": self.open_favorite}[key](idx)

    def choose_slot(self, key: str, idx: int, kind: str = "file"):
        p = self.pick_folder(tr("dlg.choose_folder")) if kind == "dir" else self.pick_file(tr("dlg.choose_program"))
        if p:
            cfg[key][idx]["path"] = os.path.normpath(p)
            self._persist()

    def open_folder(self, idx: int):
        entry = cfg["folders"][idx]
        if not entry["path"]:                      # празен слот -> избор на папка
            self.choose_slot("folders", idx, "dir")
            return
        path = expand(entry["path"])
        home = os.environ.get("USERPROFILE", os.path.expanduser("~"))

        def run():
            if not os.path.exists(path):
                if path.lower().startswith(home.lower()) and not os.path.splitext(path)[1]:
                    os.makedirs(path, exist_ok=True)            # Projects / Archive се създават при нужда
                else:
                    raise FileNotFoundError(tr("err.path_missing", path))
            start_target(path)
        self.after_close(run)

    def launch_program(self, idx: int):
        entry = cfg["programs"][idx]
        targets = [entry["path"]] if entry["path"] else DEFAULT_PROGRAMS.get(entry["id"])
        if not targets:                            # нов празен слот -> избор на програма
            self.choose_slot("programs", idx, "file")
            return
        self.after_close(lambda: self._try_targets(targets, entry["id"]))

    def launch_browser(self, idx: int):
        entry = cfg["browsers"][idx]
        bid = entry["id"]
        targets = [entry["path"]] if entry["path"] else BROWSER_CANDIDATES[bid]
        self.after_close(lambda: self._try_targets(targets, bid))

    def _try_targets(self, targets, name):
        last = None
        for t in targets:
            try:
                start_target(t)
                return
            except Exception as exc:        # пробваме следващата алтернатива
                last = exc
                log.warning("Неуспешен старт на %s: %s", t, exc)
        raise RuntimeError(f"{name}: {last}")

    def open_url(self, url: str):
        self.after_close(lambda: start_target(url))

    def open_bookmarks_folder(self):
        path = expand(cfg["bookmarks_folder"])

        def run():
            if not os.path.isdir(path):
                raise FileNotFoundError(tr("err.path_missing", path))
            start_target(path)
        self.after_close(run)

    def search_google(self, text: str):
        text = text.strip()
        if text:
            self.open_url("https://www.google.com/search?q=" + quote_plus(text))

    def open_favorite(self, idx: int):
        path = cfg["favorites"][idx]["path"]
        if not path:
            self.choose_slot("favorites", idx, "file")
            return
        self.after_close(lambda: start_target(path))

    # ------------------------------------------------------------ системни
    def system(self, sid: str):
        if sid in ("restart", "shutdown") and cfg["behavior"]["confirm_power"]:
            self.overlay.close_menu(restore=False)
            QTimer.singleShot(60, lambda: self._confirm_power(sid))
            return
        self._do_system(sid)

    def _confirm_power(self, sid):
        box = QMessageBox(QMessageBox.Question, tr("app.title"), tr(f"sys.confirm_{sid}"),
                          QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.setWindowFlag(box.windowFlags().WindowStaysOnTopHint, True)
        if box.exec() == QMessageBox.Yes:
            self._safe(lambda: self._run_system(sid))

    def _do_system(self, sid):
        self.after_close(lambda: self._run_system(sid))

    @staticmethod
    def _run_system(sid):
        if sid == "start":
            winapi.send_combo("Win")
        elif sid == "taskmgr":
            winapi.send_combo("Ctrl+Shift+Esc")
        elif sid == "settings":
            start_target("ms-settings:")
        elif sid == "lock":
            winapi.lock_workstation()
        elif sid == "sleep":
            winapi.sleep_system()
        elif sid == "restart":
            subprocess.Popen(["shutdown", "/r", "/t", "0"], creationflags=0x08000000 if sys.platform == "win32" else 0)
        elif sid == "shutdown":
            subprocess.Popen(["shutdown", "/s", "/t", "0"], creationflags=0x08000000 if sys.platform == "win32" else 0)
        elif sid == "run":
            winapi.send_combo("Win+R")

    # ------------------------------------------------------------ настройки
    def open_settings(self, page):
        self.overlay.close_menu(restore=False)
        QTimer.singleShot(30, lambda: self.c.open_settings(page))

    # ------------------------------------------------------------ избор на път (десен клик / drop)
    def _persist(self):
        cfg.save()
        self.overlay.refresh_panel()

    def pick_file(self, title):
        with self.overlay.modal():
            path, _ = QFileDialog.getOpenFileName(self.overlay, title, os.path.expandvars("%USERPROFILE%")
                                                  if sys.platform == "win32" else os.path.expanduser("~"))
        return path

    def pick_folder(self, title):
        with self.overlay.modal():
            return QFileDialog.getExistingDirectory(self.overlay, title)

    def context_menu(self, global_pos, *, on_file=None, on_folder=None, on_url=None, on_reset=None, on_remove=None):
        with self.overlay.modal():
            menu = QMenu(self.overlay)
            acts = {}
            if on_file:
                acts[menu.addAction(tr("ctx.choose_file"))] = on_file
            if on_folder:
                acts[menu.addAction(tr("ctx.choose_folder"))] = on_folder
            if on_url:
                acts[menu.addAction(tr("ctx.edit_url"))] = on_url
            if on_reset or on_remove:
                menu.addSeparator()
            if on_reset:
                acts[menu.addAction(tr("ctx.reset"))] = on_reset
            if on_remove:
                acts[menu.addAction(tr("ctx.remove"))] = on_remove
            chosen = menu.exec(global_pos)
        if chosen in acts:
            acts[chosen]()

    def ask_url(self, current: str):
        with self.overlay.modal():
            text, ok = QInputDialog.getText(self.overlay, tr("dlg.url_title"), tr("dlg.url_label"), text=current)
        return text.strip() if ok and text.strip() else None
