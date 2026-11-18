"""Горните контекстуални панели за 8-те сектора (спец. модули Б–З)."""
import logging
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from . import actions as A
from . import audio, icons
from .config import cfg
from .i18n import tr
from .layout import grid_params
from .widgets import ComboButton, Frame, KeyCap, Tile, font

log = logging.getLogger(__name__)


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


# ====================================================================== Б: клавиатура
def build_keyboard(ctx, W, H):
    s, th = ctx.s, ctx.theme
    holder = QWidget()
    holder.setFixedSize(W, H)
    gap = round(14 * s)
    sh = round(6 * s)
    vis = (W - 2 * sh - 2 * gap) / 3.0
    widths = [round(vis * 1.25), round(vis * 0.72), round(vis * 1.03)]
    x = 0
    frames = []
    for i, key in enumerate(("panel.quick_keys", "panel.std_keyboard", "panel.win_keys")):
        f = Frame(th, s, tr(key), "global", holder)
        f.setGeometry(x, 0, widths[i] + 2 * sh, H)
        x += widths[i] + gap
        frames.append(f)

    # --- ляв: бързи команди (2 реда с keycaps и „+“)
    left = frames[0]
    box = QVBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(round(4 * s))
    cont = QWidget()
    cont.setLayout(box)
    avail = widths[0] - 2 * (round(8 * s) + 0) - round(4 * s)
    for row in cfg["quick_shortcuts"]:
        items = [(it, [k for k in it["keys"].replace(" ", "").split("+") if k]) for it in row]
        need = sum(ComboButton.natural_width(tk, s) for _, tk in items) + round(5 * s) * (len(items) + 1)
        f = min(1.0, avail / need) if need else 1.0          # свива клавишите, ако комбинациите не се събират
        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(round(4 * s))
        hl.addStretch(1)
        for item, tokens in items:
            tip = tr("tip." + item.get("tip", ""))
            if not item.get("tip") or tip == "tip." + item.get("tip", ""):
                tip = item.get("tip") or item["keys"]
            btn = ComboButton(th, s * f, tokens, tip)
            btn.clicked.connect(lambda c=item["keys"]: ctx.act.keys(c))
            hl.addWidget(btn)
            hl.addStretch(1)
        box.addLayout(hl, 1)
    left.layout_.addWidget(cont, 1)

    # --- среден: стандартна клавиатура (OSK)
    mid = frames[1]
    t = Tile(th, s, "", icons.builtin("kb_keyboard"), tr("tip.osk"), icon_ratio=0.9)
    t.clicked.connect(ctx.act.osk)
    mid.layout_.addStretch(1)
    mid.layout_.addWidget(t, 3)
    mid.layout_.addStretch(1)

    # --- десен: Enter/Space/Backspace + функционални клавиши
    right = frames[2]
    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(round(6 * s))
    cont2 = QWidget()
    cont2.setLayout(col)

    def key(tok, combo, tip, close=True, noop=False):
        k = KeyCap(th, s, tok, tip)
        if not noop:
            k.clicked.connect(lambda: ctx.act.keys(combo, close=close))
        return k

    r1 = QHBoxLayout()
    r1.setSpacing(round(8 * s))
    r1.addWidget(key("enter", "Enter", tr("tip.enter")), 2)
    r1.addWidget(key("space", "Space", tr("tip.space")), 6)
    r1.addWidget(key("backspace", "Backspace", tr("tip.backspace")), 2)
    r2 = QHBoxLayout()
    r2.setSpacing(round(5 * s))
    for tok, combo, tip, st, close, noop in (
            ("win", "Win", tr("tip.win"), 14, True, False),
            ("menu", "Apps", tr("tip.menu"), 12, True, False),
            ("voldown", "VolDown", tr("tip.voldown"), 12, False, False),
            ("volup", "VolUp", tr("tip.volup"), 12, False, False),
            ("esc", "Esc", tr("tip.esc"), 13, True, False),
            ("fn", "", tr("tip.fn"), 12, True, True),
            ("altgr", "AltGr", tr("tip.altgr"), 14, True, False)):
        r2.addWidget(key(tok, combo, tip, close, noop), st)
    col.addLayout(r1, 1)
    col.addLayout(r2, 1)
    right.layout_.addWidget(cont2, 1)
    return holder


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
            label = os.path.splitext(name)[0] if os.path.isfile(os.path.expandvars(path)) else name
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

    # --- браузъри
    fb = sub(tr("sub.browsers"), 30)
    for i, e in enumerate(cfg["browsers"]):
        bid = e["id"]
        src = e["path"] or A.existing_browser_path(bid) or icons.builtin("br_" + bid)
        t = Tile(th, s, tr("browser." + bid), src, e["path"] or "", icon_ratio=0.62)
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
    fg = sub(tr("sub.google"), 32)
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

    # --- запазени сайтове
    fs = sub(tr("sub.sites"), 38)
    tf = Tile(th, s, "", icons.builtin("site_folder"), tr("site.folder"), icon_ratio=0.9)
    tf.clicked.connect(ctx.act.open_bookmarks_folder)
    fs.layout_.addWidget(tf, 1)
    for i, e in enumerate(cfg["sites"]):
        t = Tile(th, s, tr("site." + e["id"]), icons.builtin("site_" + e["id"]), e["url"], icon_ratio=0.6)
        t.clicked.connect(lambda i=i: ctx.act.open_url(cfg["sites"][i]["url"]))

        def seturl(i=i):
            u = ctx.act.ask_url(cfg["sites"][i]["url"])
            if u:
                cfg["sites"][i]["url"] = u
                ctx.act._persist()
        t.contextRequested.connect(lambda pos, a=seturl: ctx.act.context_menu(pos, on_url=a))
        fs.layout_.addWidget(t, 1)
    return main


# ====================================================================== Ж: звук
def build_sound(ctx, W, H):
    s, th = ctx.s, ctx.theme
    main = Frame(th, s, tr("panel.sound"), "global")
    main.setFixedSize(W, H)
    lay = main.layout_
    lay.setSpacing(round(8 * s))
    vol = audio.get_volume()
    muted = audio.get_mute() if vol >= 0 else False

    # --- лява зона: сила на звука
    fl = Frame(th, s, tr("sub.volume"), "sub")
    lay.addWidget(fl, 1)
    spk = Tile(th, s, "", icons.builtin("speaker_muted" if muted else "speaker_big"), icon_ratio=0.85, flat=True)
    spk.setFixedWidth(round(48 * s))
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(max(0, vol))
    slider.setEnabled(vol >= 0)
    slider.setStyleSheet(
        f"QSlider::groove:horizontal{{height:{round(6 * s)}px;background:#5A6D94;border-radius:{round(3 * s)}px;}}"
        f"QSlider::sub-page:horizontal{{background:#8FA8D8;border-radius:{round(3 * s)}px;}}"
        f"QSlider::handle:horizontal{{background:#E4E4E4;border:1px solid #333;width:{round(12 * s)}px;"
        f"height:{round(24 * s)}px;margin:-{round(9 * s)}px 0;border-radius:{round(4 * s)}px;}}"
        f"QSlider::handle:horizontal:hover{{background:#FFFFFF;}}")
    small = QLabel()
    small.setPixmap(icons.pixmap(icons.builtin("speaker_small"), round(22 * s), main.devicePixelRatioF()))
    pct = QLabel(f"{vol}%" if vol >= 0 else "—")
    pct.setFont(font(15 * s))
    pct.setStyleSheet(f"color:{th.text};")
    pct.setMinimumWidth(round(44 * s))
    for w_ in (small, pct):
        w_.setAttribute(Qt.WA_TranslucentBackground)
    fl.layout_.addWidget(spk)
    fl.layout_.addWidget(slider, 1, Qt.AlignVCenter)
    fl.layout_.addWidget(small, 0, Qt.AlignVCenter)
    fl.layout_.addWidget(pct, 0, Qt.AlignVCenter)
    if vol < 0:
        spk.setToolTip(tr("audio.unavailable"))

    def on_slide(v):
        pct.setText(f"{v}%")
        audio.set_volume(v)
    slider.valueChanged.connect(on_slide)

    state = {"muted": muted}

    def toggle():
        if vol < 0:
            return
        state["muted"] = not state["muted"]
        audio.set_mute(state["muted"])
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
    devices, default_id = audio.list_outputs()
    if devices:
        for did, name in devices:
            combo.addItem(name, did)
        idx = next((i for i, (d, _) in enumerate(devices) if d == default_id), 0)
        combo.setCurrentIndex(idx)
        state["idx"] = idx

        def on_pick(i):
            if i == state.get("idx"):
                return
            if audio.set_default_output(combo.itemData(i)):
                state["idx"] = i
            else:
                combo.setCurrentIndex(state.get("idx", 0))
                ctx.act.c.notify(tr("app.title"), tr("audio.switch_failed"))
        combo.activated.connect(on_pick)
    else:
        combo.addItem(tr("audio.no_devices") if audio.available() else tr("audio.unavailable"))
        combo.setEnabled(False)
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
