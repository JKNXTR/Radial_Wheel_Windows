"""Горните контекстуални панели за 8-те сектора (спец. модули Б–З)."""
import logging
import os

import shiboken6

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from . import actions as A
from . import audio, icons
from .config import cfg
from .i18n import tr
from .kbpanel import build_keyboard
from .layout import grid_params, internet_geom
from .widgets import ComboButton, Frame, KeyCap, Tile, font

log = logging.getLogger(__name__)


class _AudioBridge(QObject):
    """Предава резултатите от аудио нишката към GUI нишката (опашка от събития)."""
    refreshed = Signal(dict)
    switched = Signal(str, bool)


_bridge = None


def audio_bridge():
    global _bridge
    if _bridge is None:
        _bridge = _AudioBridge()
    return _bridge


class Ctx:
    """Контекст, подаван на всички builder-и."""

    def __init__(self, theme, s, act, overlay):
        self.theme, self.s, self.act, self.overlay = theme, s, act, overlay


def _tiles_frame(ctx, W, H, title, tiles, sid):
    """Рамка с решетка от плочки; подредбата идва от настройките (cfg['grid'][sid])."""
    f = Frame(ctx.theme, ctx.s, title, "global")
    f.setFixedSize(W, H)
    gp = grid_params(sid, len(tiles), ctx.s)
    cont = QWidget()
    grid = QGridLayout(cont)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(gp["gap"])
    panel_bg = cfg["grid"].get(sid, {}).get("bg", "")
    for i, t in enumerate(tiles):
        t.icon_px, t.label_px = gp["icon"], gp["font"]
        t.bg = t.bg or panel_bg
        grid.addWidget(t, i // gp["cols"], i % gp["cols"])
    for c in range(gp["cols"]):
        grid.setColumnStretch(c, 1)
    f.layout_.addWidget(cont, 1)
    return f


def _custom_icon_or(path, fallback):
    return path if path else fallback


# ====================================================================== В/Г/З: слотове (папки, програми, любими)
SLOT_KINDS = {"folders": ("folder.", "folder_"), "programs": ("app.", "app_"), "favorites": (None, None)}


def slot_visual(key, e):
    """(етикет, икона, подсказка) за един слот; ползва се и от панела, и от настройките."""
    lp, ip = SLOT_KINDS[key]
    eid, path, label = e.get("id", "custom"), e.get("path", ""), e.get("label", "")
    builtin = eid != "custom" and lp is not None
    if not label:
        if builtin:
            label = tr(lp + eid)
        elif path:
            name = os.path.basename(path.rstrip("\\/")) or path
            label = os.path.splitext(name)[0] if os.path.splitext(name)[1] else name      # без достъп до диска
        else:
            label = tr("fav.add")
    if builtin and (key == "folders" or not path):
        icon = icons.builtin(ip + eid)
    elif path:
        icon = path
    else:
        icon = icons.builtin("fav_add")
    return label, icon, os.path.expandvars(path) if path else tr("fav.empty_tip")


def _slots_panel(ctx, W, H, key, title_key):
    tiles = []
    for i, e in enumerate(cfg[key]):
        label, icon, tip = slot_visual(key, e)
        t = Tile(ctx.theme, ctx.s, label, icon, tip, bg=e.get("bg", ""))
        t.clicked.connect(lambda i=i: ctx.act.open_slot(key, i))

        def setfile(i=i):
            ctx.act.choose_slot(key, i, "file")

        def setdir(i=i):
            ctx.act.choose_slot(key, i, "dir")

        def reset(i=i):
            e = cfg[key][i]
            e["path"] = ""
            ctx.act._persist()

        def remove(i=i):
            if len(cfg[key]) > 1:
                del cfg[key][i]
                ctx.act._persist()
        t.contextRequested.connect(lambda pos, a=setfile, b=setdir, c=reset, d=remove: ctx.act.context_menu(
            pos, on_file=a, on_folder=b, on_reset=c, on_remove=d))

        def dropped(p, i=i, key=key):
            cfg[key][i]["path"] = os.path.normpath(p)        # drag & drop на .exe / .lnk / файл / папка
            ctx.act._persist()
        t.dropped.connect(dropped)
        tiles.append(t)
    return _tiles_frame(ctx, W, H, tr(title_key), tiles, key)


def build_folders(ctx, W, H):
    return _slots_panel(ctx, W, H, "folders", "panel.folders")


def build_programs(ctx, W, H):
    return _slots_panel(ctx, W, H, "programs", "panel.programs")


def build_favorites(ctx, W, H):
    return _slots_panel(ctx, W, H, "favorites", "panel.favorites")


# ====================================================================== Д: настройки
def build_settings(ctx, W, H):
    names = ["view", "layout", "icons", "functions", "themes", "hotkeys", "sounds", "reset"]
    tiles = []
    for n in names:
        t = Tile(ctx.theme, ctx.s, tr("set." + n), icons.builtin("set_" + n))
        t.clicked.connect(lambda n=n: ctx.act.open_settings(n))
        tiles.append(t)
    return _tiles_frame(ctx, W, H, tr("panel.settings"), tiles, "settings")


# ====================================================================== З: системни команди
def build_system(ctx, W, H):
    tiles = []
    for sid in A.SYSTEM_ACTIONS:
        t = Tile(ctx.theme, ctx.s, tr("sys." + sid), icons.builtin("sys_" + sid))
        t.clicked.connect(lambda sid=sid: ctx.act.system(sid))
        tiles.append(t)
    return _tiles_frame(ctx, W, H, tr("panel.system"), tiles, "system")


# ====================================================================== Е: интернет
def build_internet(ctx, W, H):
    s, th = ctx.s, ctx.theme
    main = Frame(th, s, tr("panel.internet"), "global")
    main.setFixedSize(W, H)
    lay = main.layout_
    lay.setSpacing(round(8 * s))

    def sub(title, stretch):
        f = Frame(th, s, title, "sub")
        f.layout_.setSpacing(round(4 * s))
        f.pad = round(5 * s)
        lay.addWidget(f, stretch)
        return f

    # --- браузъри (вградена икона; системна икона само за зададен собствен път – и тя се кешира)
    geo = internet_geom(s, W, H)
    fb = sub(tr("sub.browsers"), 0)
    fb.setFixedWidth(geo["bw"])
    for i, e in enumerate(cfg["browsers"]):
        bid = e["id"]
        known = bid in A.BROWSER_CANDIDATES
        src = e["path"] if e["path"] else (icons.builtin("br_" + bid) if known else icons.builtin("sector_internet"))
        label = e.get("label") or (tr("browser." + bid) if known else os.path.splitext(os.path.basename(e["path"]))[0] or tr("browser.custom"))
        t = Tile(th, s, label, src, e["path"] or "", icon_ratio=0.62)
        t.clicked.connect(lambda i=i: ctx.act.launch_browser(i))

        def setp(i=i):
            p = ctx.act.pick_file(tr("dlg.choose_program"))
            if p:
                cfg["browsers"][i]["path"] = os.path.normpath(p)
                ctx.act._persist()

        def reset(i=i):
            cfg["browsers"][i]["path"] = ""
            ctx.act._persist()
        t.contextRequested.connect(lambda pos, a=setp, r=reset: ctx.act.context_menu(pos, on_file=a, on_reset=r))
        fb.layout_.addWidget(t, 1)

    # --- Google търсене
    fg = sub(tr("sub.google"), 0)
    fg.setFixedWidth(geo["gw"])
    edit = QLineEdit()
    edit.setObjectName("searchEdit")
    edit.setClearButtonEnabled(False)
    from PySide6.QtGui import QAction, QIcon
    gact = QAction(QIcon(icons.builtin("google_g")), "", edit)
    edit.addAction(gact, QLineEdit.LeadingPosition)
    sact = QAction(QIcon(icons.builtin("search")), "", edit)
    edit.addAction(sact, QLineEdit.TrailingPosition)
    edit.setStyleSheet(
        f"QLineEdit#searchEdit{{background:{th.input_bg};color:{th.input_text};border:1px solid #444;"
        f"border-radius:{round(5 * s)}px;padding:{round(3 * s)}px {round(6 * s)}px;"
        f"font-family:'Segoe UI';font-size:{round(14 * s)}px;selection-background-color:{th.active_top};}}")
    edit.setFixedHeight(round(32 * s))
    btn = QPushButton(tr("search.button"))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(round(32 * s))
    btn.setStyleSheet(
        f"QPushButton{{background:{th.tile_bg};color:{th.text};border:1px solid {th.tile_border};border-radius:{round(5 * s)}px;"
        f"padding:0 {round(12 * s)}px;font-family:'Segoe UI';font-size:{round(14 * s)}px;}}"
        f"QPushButton:hover{{background:{th.tile_hover};border-color:{th.active_border};}}")
    do_search = lambda: ctx.act.search_google(edit.text())     # noqa: E731
    edit.returnPressed.connect(do_search)
    btn.clicked.connect(do_search)
    sact.triggered.connect(do_search)
    row = QHBoxLayout()
    row.setSpacing(round(6 * s))
    row.addWidget(edit, 1)
    row.addWidget(btn)
    w = QWidget()
    w.setLayout(row)
    fg.layout_.addWidget(w, 1, Qt.AlignVCenter)
    ctx.overlay.focus_widget = edit if cfg["behavior"]["autofocus_search"] else None

    # --- запазени сайтове: решетка (колони/редове от настройките), цвят и икона за всеки сайт
    fs = sub(tr("sub.sites"), 1)
    cont = QWidget()
    grid = QGridLayout(cont)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(round(5 * s))
    panel_bg = cfg["grid"].get("internet", {}).get("bg", "")
    tf = Tile(th, s, "", icons.builtin("site_folder"), tr("site.folder"), icon_ratio=0.9, bg=panel_bg)
    tf.clicked.connect(ctx.act.open_bookmarks_folder)
    grid.addWidget(tf, 0, 0)
    for i, e in enumerate(cfg["sites"]):
        known = e["id"] in ("favorites", "news", "mail", "social")
        label = e.get("label") or (tr("site." + e["id"]) if known else e["url"].split("//")[-1].split("/")[0])
        icon = e.get("icon") or (icons.builtin("site_" + e["id"]) if known else icons.builtin("site_favorites"))
        t = Tile(th, s, label, icon, e["url"], icon_ratio=0.6, bg=e.get("bg") or panel_bg)
        t.clicked.connect(lambda i=i: ctx.act.open_url(cfg["sites"][i]["url"]))

        def seturl(i=i):
            u = ctx.act.ask_url(cfg["sites"][i]["url"])
            if u:
                cfg["sites"][i]["url"] = u
                ctx.act._persist()

        def remove(i=i):
            del cfg["sites"][i]
            ctx.act._persist()
        t.contextRequested.connect(lambda pos, a=seturl, r=remove: ctx.act.context_menu(pos, on_url=a, on_remove=r))
        n = i + 1
        grid.addWidget(t, n // geo["cols"], n % geo["cols"])
    for c in range(geo["cols"]):
        grid.setColumnStretch(c, 1)
    fs.layout_.addWidget(cont, 1)
    return main


# ====================================================================== Ж: звук
def build_sound(ctx, W, H):
    s, th = ctx.s, ctx.theme
    main = Frame(th, s, tr("panel.sound"), "global")
    main.setFixedSize(W, H)
    lay = main.layout_
    lay.setSpacing(round(8 * s))
    snap = audio.snapshot()                    # последни известни стойности; без COM в GUI нишката
    vol = snap["vol"]
    muted = snap["muted"]
    bridge = audio_bridge()

    # --- лява зона: сила на звука
    fl = Frame(th, s, tr("sub.volume"), "sub")
    lay.addWidget(fl, 1)
    spk = Tile(th, s, "", icons.builtin("speaker_muted" if muted else "speaker_big"), icon_ratio=0.85, flat=True)
    spk.setFixedWidth(round(48 * s))
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(max(0, vol))
    slider.setEnabled(vol >= 0)
    state_vol = {"ok": vol >= 0}
    slider.setStyleSheet(
        f"QSlider::groove:horizontal{{height:{round(6 * s)}px;background:#5A6D94;border-radius:{round(3 * s)}px;}}"
        f"QSlider::sub-page:horizontal{{background:#8FA8D8;border-radius:{round(3 * s)}px;}}"
        f"QSlider::handle:horizontal{{background:#E4E4E4;border:1px solid #333;width:{round(12 * s)}px;"
        f"height:{round(24 * s)}px;margin:-{round(9 * s)}px 0;border-radius:{round(4 * s)}px;}}"
        f"QSlider::handle:horizontal:hover{{background:#FFFFFF;}}")
    small = QLabel()
    small.setPixmap(icons.pixmap(icons.builtin("speaker_small"), round(22 * s), main.devicePixelRatioF()))
    pct = QLabel(f"{vol}%" if vol >= 0 else "…" if audio.available() else "—")
    pct.setFont(font(15 * s))
    pct.setStyleSheet(f"color:{th.text};")
    pct.setMinimumWidth(round(44 * s))
    for w_ in (small, pct):
        w_.setAttribute(Qt.WA_TranslucentBackground)
    fl.layout_.addWidget(spk)
    fl.layout_.addWidget(slider, 1, Qt.AlignVCenter)
    fl.layout_.addWidget(small, 0, Qt.AlignVCenter)
    fl.layout_.addWidget(pct, 0, Qt.AlignVCenter)
    if vol < 0 and not audio.available():
        spk.setToolTip(tr("audio.unavailable"))

    def on_slide(v):
        pct.setText(f"{v}%")
        audio.set_volume_async(v)
    slider.valueChanged.connect(on_slide)

    state = {"muted": muted}

    def toggle():
        if not state_vol["ok"]:
            return
        state["muted"] = not state["muted"]
        audio.set_mute_async(state["muted"])
        spk.set_icon(icons.builtin("speaker_muted" if state["muted"] else "speaker_big"))
    spk.clicked.connect(toggle)

    # --- дясна зона: аудио изходи
    fr = Frame(th, s, tr("sub.devices"), "sub")
    lay.addWidget(fr, 1)
    combo = QComboBox()
    combo.setObjectName("wheelCombo")
    arrow = icons.builtin("arrow_down").replace("\\", "/")
    combo.setStyleSheet(
        f"QComboBox#wheelCombo{{background:#1E1E1E;color:{th.text};border:1px solid #111;border-radius:{round(4 * s)}px;"
        f"padding:{round(3 * s)}px {round(8 * s)}px;font-family:'Segoe UI';font-size:{round(15 * s)}px;min-height:{round(24 * s)}px;}}"
        f"QComboBox#wheelCombo:hover{{border-color:{th.active_border};}}"
        f"QComboBox#wheelCombo::drop-down{{border:none;width:{round(26 * s)}px;}}"
        f"QComboBox#wheelCombo::down-arrow{{image:url({arrow});width:{round(12 * s)}px;height:{round(12 * s)}px;}}"
        f"QComboBox#wheelCombo QAbstractItemView{{background:#1E1E1E;color:{th.text};border:1px solid #111;"
        f"selection-background-color:#33363F;selection-color:{th.text};outline:0;font-size:{round(15 * s)}px;}}")
    cstate = {"ids": None}

    def fill(devices, default_id):
        ids = [d for d, _ in devices]
        if ids == cstate["ids"]:
            idx = ids.index(default_id) if default_id in ids else 0
            if ids and combo.currentIndex() != idx:
                combo.blockSignals(True)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)
            return
        cstate["ids"] = ids
        combo.blockSignals(True)
        combo.clear()
        if devices:
            for did, name in devices:
                combo.addItem(name, did)
            idx = ids.index(default_id) if default_id in ids else 0
            combo.setCurrentIndex(idx)
            state["idx"] = idx
            combo.setEnabled(True)
        else:
            combo.addItem(tr("audio.no_devices") if audio.available() else tr("audio.unavailable"))
            combo.setEnabled(False)
        combo.blockSignals(False)

    def on_pick(i):
        if i == state.get("idx") or combo.itemData(i) is None:
            return
        state["want"] = i
        combo.setEnabled(False)
        audio.set_default_output_async(combo.itemData(i), lambda ok, did=combo.itemData(i): bridge.switched.emit(did, ok))
    combo.activated.connect(on_pick)

    def on_switched(did, ok):
        if not shiboken6.isValid(combo):
            return
        combo.setEnabled(True)
        if ok:
            state["idx"] = state.get("want", state.get("idx", 0))
        else:
            combo.setCurrentIndex(state.get("idx", 0))
            ctx.act.c.notify(tr("app.title"), tr("audio.switch_failed"))

    def on_refreshed(snap):
        if not shiboken6.isValid(main):
            return
        if snap["vol"] >= 0:
            state_vol["ok"] = True
            slider.blockSignals(True)
            slider.setValue(snap["vol"])
            slider.blockSignals(False)
            slider.setEnabled(True)
            pct.setText(f"{snap['vol']}%")
            spk.setToolTip("")
        state["muted"] = snap["muted"]
        spk.set_icon(icons.builtin("speaker_muted" if snap["muted"] else "speaker_big"))
        if not slider.isSliderDown():
            fill(snap["devices"], snap["default"])

    fill(snap["devices"], snap["default"])
    bridge.refreshed.connect(on_refreshed)
    bridge.switched.connect(on_switched)

    def cleanup(*_):
        for sig, fn in ((bridge.refreshed, on_refreshed), (bridge.switched, on_switched)):
            try:
                sig.disconnect(fn)
            except Exception:
                pass
    main.destroyed.connect(cleanup)
    audio.refresh_async(lambda sn: bridge.refreshed.emit(sn))
    fr.layout_.addStretch(1)
    fr.layout_.addWidget(combo, 6, Qt.AlignVCenter)
    fr.layout_.addStretch(1)
    return main


BUILDERS = {
    "keyboard": build_keyboard,
    "folders": build_folders,
    "system": build_system,
    "favorites": build_favorites,
    "sound": build_sound,
    "internet": build_internet,
    "settings": build_settings,
    "programs": build_programs,
}
