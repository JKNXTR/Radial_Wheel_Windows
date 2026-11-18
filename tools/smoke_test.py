"""Headless тест на логиката (без Windows): hit-testing, конфиг, hover/click поведение, панели, настройки.

  python tools/smoke_test.py
"""
import math
import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from PySide6.QtCore import QPointF, Qt              # noqa: E402
from PySide6.QtWidgets import QApplication          # noqa: E402

from radialwheel import actions, winapi             # noqa: E402
from radialwheel.config import DEFAULTS, SECTOR_IDS, cfg   # noqa: E402
from radialwheel.i18n import set_language, tr       # noqa: E402
from radialwheel.overlay import Overlay             # noqa: E402
from radialwheel.panels import BUILDERS             # noqa: E402
from radialwheel.wheel import CENTER, NONE, sector_at     # noqa: E402

failed = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if extra and not cond else ""))
    if not cond:
        failed.append(name)


class FakeController:
    def __init__(self):
        self.notes = []
        self.settings_page = None

    def notify(self, t, m):
        self.notes.append(m)

    def open_settings(self, p):
        self.settings_page = p


def main():
    app = QApplication([])
    # 1. hit-testing: 8 посоки + границите на 22.5°
    for i in range(8):
        a = math.radians(i * 45)
        check(f"sector_at център на сектор {i}", sector_at(math.sin(a), -math.cos(a)) == i)
    for i in range(8):
        for d in (-22.4, 22.4):
            a = math.radians(i * 45 + d)
            check(f"sector_at край {i}{d:+}", sector_at(math.sin(a), -math.cos(a)) == i)
    check("sector_at 12:00 / 6:00 / 3:00 / 9:00",
          [sector_at(0, -1), sector_at(0, 1), sector_at(1, 0), sector_at(-1, 0)] == [0, 4, 2, 6])

    # 2. конфиг
    cfg.load()
    check("конфиг по подразбиране", cfg["sector_order"] == SECTOR_IDS and len(cfg["folders"]) == 8)
    cfg["appearance"]["scale"] = 9
    cfg.data["sector_order"] = ["x"]
    cfg._sanitize()
    check("sanitize коригира невалидни стойности", cfg["appearance"]["scale"] == 2.0 and cfg["sector_order"] == SECTOR_IDS)
    cfg.reset()
    cfg.load()
    check("reset+load", cfg["appearance"]["scale"] == 1.0)

    # 3. i18n
    set_language("bg")
    check("i18n bg", tr("panel.sound") == "Звукови Настройки")
    set_language("en")
    check("i18n en", tr("panel.sound") == "Sound Settings")
    set_language("bg")
    import json
    import re
    from radialwheel.paths import LANG
    bg = json.loads((LANG / "lang_bg.json").read_text(encoding="utf-8"))
    en = json.loads((LANG / "lang_en.json").read_text(encoding="utf-8"))
    check("lang файловете имат еднакви ключове", set(bg) == set(en), str(set(bg) ^ set(en)))

    # 4. overlay + hover/click
    Overlay._fit_scale = lambda self, screen: 1.0
    cfg["behavior"]["hover_delay_ms"] = 0
    cfg["sounds"] = False
    ctl = FakeController()
    ov = Overlay(ctl)
    ctl.overlay = ov
    ov.show()
    w = ov.wheel
    check("колелото е центрирано", abs(w.c.x() - w.width() / 2) < 1)
    seen = []
    w.hovered.connect(seen.append)
    w.track(QPointF(w.c.x(), w.c.y()))
    check("центърът е неутрален при отваряне", not w.center_hot and w.active == NONE)
    r = (w.R + w.r) / 2
    for i, sid in enumerate(cfg["sector_order"]):
        a = math.radians(i * 45)
        w.track(QPointF(w.c.x() + r * math.sin(a), w.c.y() - r * math.cos(a)))
        check(f"hover сектор {i} отваря панел {sid}", ov.panel_sid == sid and ov.panel is not None)
    w.track(QPointF(w.c.x() + w.R + 30, w.c.y()))
    check("извън колелото изборът е „залепнал“", w.active == 7)
    w.track(QPointF(w.c.x(), w.c.y() + 3))
    check("hover център -> Delete + скрит панел", w.center_hot and ov.panel is None)
    # клик режим
    cfg["behavior"]["open_mode"] = "click"
    ov._clear_panel()
    w.reset_state()
    w._armed = True
    w.track(QPointF(w.c.x(), w.c.y() - r))
    check("click режим: hover не отваря панел", ov.panel is None)
    w.sectorClicked.emit(0)
    check("click режим: клик отваря панел", ov.panel_sid == "keyboard")
    cfg["behavior"]["open_mode"] = "hover"

    # 4b. жизнен цикъл: pin / X / two-step dismiss
    cfg["behavior"]["hover_delay_ms"] = 0
    ov.hide()
    ov.popup()
    w = ov.wheel
    w.track(QPointF(w.c.x(), w.c.y() - r))
    check("hover отваря непиннат панел", ov.panel_sid == "keyboard" and not ov.pinned)
    w.sectorClicked.emit(0)
    w.locked = True
    ov.pinned = True
    w.track(QPointF(w.c.x() + r, w.c.y()))
    check("pinned: hover върху друг сектор не сменя панела", ov.panel_sid == "keyboard")
    from radialwheel.widgets import Frame
    frames = ov.panel.findChildren(Frame)
    check("всеки глобален панел има X", len(frames) == 3 and all(f.has_close for f in frames))
    frames[0].closeRequested.emit()
    check("X затваря само панела, колелото остава", ov.panel is None and ov.isVisible() and not ov.pinned)
    check("след затваряне колелото е в изходно състояние", w.active == NONE and not w.locked)
    w.track(QPointF(w.c.x() + r, w.c.y()))
    check("след X hover отново работи", ov.panel_sid == "system")
    ov.outside_click()
    check("1-ви клик извън затваря панела", ov.panel is None and ov.isVisible())
    ov.outside_click()
    check("2-ри клик извън скрива инструмента", not ov.isVisible())
    ov.popup()
    check("hotkey toggle отваря", ov.isVisible())
    ov.popup()
    check("повторен hotkey затваря", not ov.isVisible())
    ov.popup()
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    ov.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    check("Esc затваря", not ov.isVisible())
    ov.popup()
    w.centerClicked.emit()
    check("клик върху Delete затваря", not ov.isVisible())
    ov.hide()

    # 5. всички панели се изграждат без грешки и на различни мащаби
    for s in (0.6, 1.0, 1.5, 2.0):
        cfg["appearance"]["scale"] = s
        Overlay._fit_scale = lambda self, screen, s=s: s
        ov.rebuild()
        for sid in SECTOR_IDS:
            try:
                wdg = BUILDERS[sid](ov.ctx, *ov.dims[sid])
                wdg.show()
                app.processEvents()
                ok = True
            except Exception:
                traceback.print_exc()
                ok = False
            check(f"панел {sid} @ {s}", ok)
    cfg["appearance"]["scale"] = 1.0
    Overlay._fit_scale = lambda self, screen: 1.0
    ov.rebuild()

    # 6. winapi
    check("parse_combo", winapi.parse_combo("Shift+Win+S") == [0xA0, 0x5B, ord("S")])
    check("parse_combo стрелки", winapi.parse_combo("Alt+Left") == [0xA4, 0x25])
    try:
        winapi.parse_combo("Ctrl+Foo")
        check("parse_combo невалиден клавиш хвърля грешка", False)
    except ValueError:
        check("parse_combo невалиден клавиш хвърля грешка", True)
    for _, row in enumerate(cfg["quick_shortcuts"]):
        for it in row:
            winapi.parse_combo(it["keys"])
    check("всички quick_shortcuts са валидни", True)

    # 7. actions
    check("DEFAULT_PROGRAMS покрива всички слотове", all(p["id"] in actions.DEFAULT_PROGRAMS for p in DEFAULTS["programs"]))

    # 7b. слушател на клавиша
    from radialwheel.listener import hotkey_from_config
    check("listener: клавиш по подразбиране", hotkey_from_config(DEFAULTS) == (0x1 | 0x2, 0x20))
    off = {"hotkey": {"enabled": False}}
    check("listener: изключен клавиш", hotkey_from_config(off) is None)
    check("listener: Ctrl+Alt+Shift+Q", hotkey_from_config({"hotkey": {"enabled": True, "ctrl": True, "alt": True, "shift": True, "win": False, "key": "Q"}}) == (0x7, ord("Q")))
    from radialwheel import lifecycle
    check("lifecycle команда", lifecycle.base_command()[-1].endswith("main.py"))

    # 7c. решетка, динамични слотове, Delete
    from radialwheel.layout import grid_params
    cfg["grid"]["folders"].update(mode="per_row", value=4)
    gp = grid_params("folders", 8, 1.0)
    check("решетка: 8 слота по 4 на ред = 4×2", gp["cols"] == 4 and gp["rows"] == 2)
    cfg["grid"]["folders"].update(mode="rows", value=3)
    gp = grid_params("folders", 8, 1.0)
    check("решетка: 3 реда за 8 слота = 3 колони", gp["cols"] == 3 and gp["rows"] == 3)
    cfg["grid"]["folders"].update(mode="single")
    check("решетка: един ред", grid_params("folders", 8, 1.0)["rows"] == 1)
    base_h = grid_params("folders", 8, 1.0)["H"]
    cfg["grid"]["folders"].update(tile_w=120, tile_h=100)
    g2 = grid_params("folders", 8, 1.0)
    check("размер на плочка се прилага", g2["tile_w"] == 120 and g2["H"] > base_h)
    cfg["grid"]["folders"].update(tile_w=0, tile_h=0)
    # добавяне на слот през настройките, нов празен слот и много слотове
    n0 = len(cfg["folders"])
    cfg["folders"].append({"id": "custom", "path": "", "label": ""})
    cfg["grid"]["folders"].update(mode="per_row", value=5)
    Overlay._fit_scale = lambda self, screen: 1.0
    ov.rebuild()
    wdg = BUILDERS["folders"](ov.ctx, *ov.dims["folders"])
    wdg.show()
    from radialwheel.widgets import Tile
    check("нов слот се показва като плочка", len(wdg.findChildren(Tile)) == n0 + 1)
    check("зоната на прозореца побира най-големия панел", ov.zone_h >= ov.dims["folders"][1])
    for _ in range(30):
        cfg["programs"].append({"id": "custom", "path": "", "label": ""})
    ov.rebuild()
    BUILDERS["programs"](ov.ctx, *ov.dims["programs"]).show()
    check("30+ слота се изграждат", True)
    # Delete бутон -> клавиш Delete
    sent = []
    actions.winapi.send_combo = lambda c: sent.append(c)
    ov.hide(); ov.popup()
    ov.wheel.centerHeld.emit()
    import time as _t
    for _ in range(10):
        app.processEvents(); _t.sleep(0.03)
    check("клик върху Delete праща клавиша Delete и скрива колелото", sent == ["Delete"] and not ov.isVisible(), str(sent))
    cfg.reset()
    cfg["behavior"]["hover_delay_ms"] = 0
    ov.rebuild()
    r = (ov.wheel.R + ov.wheel.r) / 2

    # 7e. цвят на плочки, редове/колони на комбинациите, център
    cfg["grid"]["folders"]["bg"] = "#80FF0000"
    ov.rebuild()
    wd = BUILDERS["folders"](ov.ctx, *ov.dims["folders"])
    check("фонът на плочките се прилага", all(t.bg == "#80FF0000" for t in wd.findChildren(Tile)))
    cfg["grid"]["folders"]["bg"] = ""
    cfg["quick_shortcuts"] = [[{"keys": "Ctrl+A", "tip": "a"}] * 4, [{"keys": "Ctrl+B", "tip": "b"}] * 2, [{"keys": "Ctrl+D", "tip": "d"}]]
    ov.rebuild()
    kb = BUILDERS["keyboard"](ov.ctx, *ov.dims["keyboard"])
    from radialwheel.widgets import ComboButton
    check("комбинации: 3 реда, 7 бутона", len(kb.findChildren(ComboButton)) == 7, str(len(kb.findChildren(ComboButton))))
    cfg.reset(); cfg["behavior"]["hover_delay_ms"] = 0
    ov.rebuild()
    wh = ov.wheel
    wh.reset_state()
    wh.mouseMoveEvent(type("E", (), {"position": lambda self: QPointF(wh.c.x() + 1, wh.c.y())})())
    check("центърът е неутрален при появата", not wh.center_hot)
    wh.mouseMoveEvent(type("E", (), {"position": lambda self: QPointF(wh.c.x() + 6, wh.c.y())})())
    check("центърът става червен след движение вътре в него", wh.center_hot)

    # 7f. езици
    from radialwheel.i18n import LANGUAGES
    check("20+ езика, включен български", len(LANGUAGES) >= 20 and "bg" in LANGUAGES and "en" in LANGUAGES)
    check("езикът по подразбиране е английски", __import__("radialwheel.config", fromlist=["DEFAULTS"]).DEFAULTS["language"] == "en")
    en_d = json.loads((LANG / "lang_en.json").read_text(encoding="utf-8"))
    for code in LANGUAGES:
        d = json.loads((LANG / f"lang_{code}.json").read_text(encoding="utf-8"))
        extra = set(d) - set(en_d) - {"language.name"}
        ph_ok = all(sorted(re.findall(r"\{\d\}", v)) == sorted(re.findall(r"\{\d\}", en_d.get(k, ""))) for k, v in d.items() if k in en_d)
        check(f"език {code}: ключове и {{}} са коректни", not extra and ph_ok, str(extra))
        set_language(code)
        check(f"език {code}: tr работи", tr("sector.keyboard") not in ("", "sector.keyboard"))
    set_language("en")

    # 7g. център: кратък клик = Backspace, задържане = Delete с пръстен
    from PySide6.QtCore import QEvent, QPointF as _P, Qt as _Qt
    from PySide6.QtGui import QMouseEvent
    import time as _t2
    sent2 = []
    actions.winapi.send_combo = lambda c: sent2.append(c)

    def mouse(kind, pos):
        return QMouseEvent(kind, pos, pos, _Qt.LeftButton, _Qt.LeftButton if kind == QEvent.MouseButtonPress else _Qt.NoButton, _Qt.NoModifier)
    ov.hide(); ov.popup(); wh = ov.wheel
    cpos = wh.c
    wh.mousePressEvent(mouse(QEvent.MouseButtonPress, cpos))
    wh.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, cpos))
    for _ in range(10):
        app.processEvents(); _t2.sleep(0.03)
    check("кратък клик върху центъра праща Backspace", sent2 == ["Backspace"], str(sent2))
    sent2.clear(); ov.hide(); ov.popup(); wh = ov.wheel
    wh.mousePressEvent(mouse(QEvent.MouseButtonPress, wh.c))
    _t2.sleep(0.5)
    app.processEvents()
    check("пръстенът се пълни при задържане", 0.2 < wh._hold < 0.9, str(wh._hold))
    wh.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, wh.c))
    check("ранно пускане нулира пръстена", wh._hold == 0)
    for _ in range(10):
        app.processEvents(); _t2.sleep(0.03)          # изчакваме Backspace от ранното пускане
    sent2.clear(); ov.hide(); ov.popup(); wh = ov.wheel
    wh.mousePressEvent(mouse(QEvent.MouseButtonPress, wh.c))
    t0 = _t2.time()
    while _t2.time() - t0 < 1.6 and not sent2:
        app.processEvents(); _t2.sleep(0.02)
    for _ in range(10):
        app.processEvents(); _t2.sleep(0.03)
    check("задържане ~1 s праща Delete", sent2 == ["Delete"], str(sent2))
    wh.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, wh.c))
    check("след Delete пускането не праща Backspace", sent2 == ["Delete"], str(sent2))

    # 7h. звукът не блокира GUI нишката; кеш; отдалечени пътища; watchdog
    import time as _t3
    from radialwheel import audio as _au, icons as _ic
    calls = []
    _au.get_volume = lambda: calls.append("vol") or 50
    _au.list_outputs = lambda: calls.append("list") or ([], None)
    t0 = _t3.perf_counter()
    BUILDERS["sound"](ov.ctx, *ov.dims["sound"]).show()
    check("панелът за звук се изгражда без COM заявки", not calls and _t3.perf_counter() - t0 < 0.5, str(calls))
    check("UNC пътят се разпознава като отдалечен", _ic._is_remote("\\\\server\\share\\a.exe"))
    check("локален път не е отдалечен", not _ic._is_remote("/tmp/a.png"))
    from radialwheel import watchdog
    check("watchdog модул се зарежда", hasattr(watchdog, "start"))

    # 7i. стари/увиснали екземпляри се затварят
    import subprocess as _sp, sys as _sys
    from radialwheel import lifecycle as _lc
    main_py = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
    import psutil as _ps
    spawn = ("import subprocess,sys;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)',sys.argv[1],'--listener'],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL);print(p.pid)")
    pid = int(_sp.check_output([_sys.executable, "-c", spawn, main_py]).strip())      # сирак: не е наш наследник
    _t3.sleep(0.4)
    check("млад процес (паралелен старт) не се пипа", _lc.kill_stale(min_age=30.0) == 0 and _ps.pid_exists(pid))
    n = _lc.kill_stale(min_age=0.0, wait=2.0)
    _t3.sleep(0.3)
    check("kill_stale затваря увисналия процес", n >= 1 and not (_ps.pid_exists(pid) and _ps.Process(pid).status() != "zombie"), str(n))

    # 7n. увеличение на избрания сектор
    cfg.reset(); cfg["behavior"]["hover_delay_ms"] = 0
    ov.rebuild()
    zl = ov.zoom_layer
    def _spin(sec):
        t0 = _t3.time()
        while _t3.time() - t0 < sec:
            app.processEvents(); _t3.sleep(0.01)
    ov.wheel.active = 3; ov.wheel.changed.emit(); _spin(0.7)
    check("избран сектор се увеличава плавно до ×2 (z≈1)", zl.z[3] > 0.99 and max(zl.z[i] for i in range(8) if i != 3) == 0.0, str(zl.z))
    ov.wheel.active = 5; ov.wheel.changed.emit(); _spin(0.12)
    check("при смяна: предишният се свива, новият расте (междинно състояние)", 0.0 < zl.z[3] < 1.0 and 0.0 < zl.z[5] < 1.0, str(zl.z))
    _spin(0.7)
    check("предишният сектор се връща в оригинал (z=0), новият ×2", zl.z[3] == 0.0 and zl.z[5] > 0.99)
    ov.wheel.center_hot = True; ov.wheel.changed.emit(); _spin(0.7)
    check("център (Delete) не увеличава сектор", max(zl.z) == 0.0)
    ov.wheel.center_hot = False; ov.wheel.active = -1
    pm = ov.grab()
    check("overlay се рисува със слоя без грешки", not pm.isNull())

    # 7o. настройки „Анимация“, плавно червено на центъра, затъмняване, отдалечаване
    from radialwheel import settings_dialog as _sd
    check("страница „Анимация“ е в менюто", "animation" in _sd.PAGES)
    cfg["animation"].update(push_on=True, push=10, dim_on=True, dim=50)
    cfg["animation"]["zoom"]["sound"] = 1.5
    ov.rebuild(); zl = ov.zoom_layer; w_ = ov.wheel
    ov.wheel.active = 4; ov.wheel.changed.emit(); _spin(0.8)    # позиция 4 = в реда по подразбиране 'sound'
    sid4 = cfg["sector_order"][4]
    check("затъмняване: останалите сектори са по-прозрачни", abs(zl.dim - 1.0) < 0.01 and abs(w_._sector_opacity(1, zl, 0.5) - 0.5) < 0.01 and w_._sector_opacity(4, zl, 0.5) == 1.0)
    check("отдалечаване (push) и размер по сектор са в конфигурацията", cfg["animation"]["push_on"] and cfg["animation"]["zoom"]["sound"] == 1.5)
    ov.grab()
    w_.active = -1; w_.center_hot = True; w_.changed.emit(); w_._kick_center(); _spin(0.12)
    check("център: червеното нараства плавно (междинно)", 0.0 < w_._ct < 0.95, f"{w_._ct}")
    _spin(0.8)
    check("център: напълно червен след прехода", w_._ct > 0.99)
    w_._hold = 1.0; w_._holding = True; w_._kick_center(); _spin(0.6)
    check("център: при задържане по-ярко/по-голямо (hb→1)", w_._hb > 0.95, f"{w_._hb}")
    ov.grab()
    w_._holding = False; w_._hold = 0.0; w_.center_hot = False; _spin(0.8)
    check("център: плавно връщане към сиво", w_._ct < 0.01 and w_._hb < 0.01, f"{w_._ct} {w_._hb}")
    w_._hold = 0.0; w_._lt = 0.0; w_.center_hot = True; w_._kick_center(); _spin(0.5)
    check("център: първоначален надпис е Backspace (lt=0)", w_._lt < 0.01)
    w_._hold = 1.0; w_._holding = True; w_._kick_center(); _spin(0.6)
    check("център: при задържане надписът се сменя към Delete (lt→1)", w_._lt > 0.95, f"{w_._lt}")
    ov.grab()
    w_._holding = False; w_._hold = 0.0; w_.center_hot = False; _spin(0.6)
    cfg["appearance"]["animations"] = False
    w_.center_hot = True; w_._kick_center(); _spin(0.1)
    check("анимации изключени: центърът е мигновено червен", w_._ct == 1.0)
    cfg["appearance"]["animations"] = True
    cfg.reset(); cfg["behavior"]["hover_delay_ms"] = 0

    # 7m. надзорник: срив -> рестарт, код 0 -> край
    import types, tempfile, textwrap
    from radialwheel import supervisor as _sv
    _sv.RESTART_DELAY = 0.3
    tdir = tempfile.mkdtemp()
    cnt = os.path.join(tdir, "n")
    fake = os.path.join(tdir, "fake.py")
    open(fake, "w").write(textwrap.dedent(f"""
        import sys
        p = r'{cnt}'
        n = int(open(p).read()) if __import__('os').path.exists(p) else 0
        open(p, 'w').write(str(n + 1))
        sys.exit(1 if n < 2 else 0)
    """))
    _old_argv = sys.argv[0]
    sys.argv[0] = fake
    rc = _sv.run(types.SimpleNamespace(autostart=False, show=False))
    sys.argv[0] = _old_argv
    check("надзорник: 2 срива -> 3 старта, после нормален изход", rc == 0 and open(cnt).read() == "3", open(cnt).read())

    # 7l. COM никога не се зарежда в GUI нишката
    _au.available()
    check("audio.available() не импортира comtypes/pycaw", "comtypes" not in sys.modules and "pycaw" not in sys.modules)

    # 7k. ресурси
    from radialwheel import resources as _res
    check("resources.check работи и връща MB", _res.check() >= 0)
    _res.trim()

    # 7j. Интернет панел, миграция на браузърите, разгъваща се клавиатура
    from radialwheel.config import Config as _Cfg
    c2 = _Cfg.__new__(_Cfg)
    c2.data = {k: v for k, v in __import__("copy").deepcopy(cfg.data).items()}
    c2.data["browsers"] = [{"id": i, "path": ""} for i in ("chrome", "firefox", "edge", "opera")]
    c2._sanitize()
    check("стари 4 браузъра -> Chrome и Edge", [b["id"] for b in c2.data["browsers"]] == ["chrome", "edge"])
    cfg["sites"] = [{"id": "custom", "url": f"https://s{i}.example", "label": f"S{i}", "icon": "", "bg": "#80FF0000"} for i in range(9)]
    cfg["grid"]["internet"].update(mode="per_row", value=4)
    ov.rebuild()
    wi = BUILDERS["internet"](ov.ctx, *ov.dims["internet"]); wi.show()
    from radialwheel.widgets import Tile as _T
    check("Интернет: 2 браузъра + папка + 9 сайта плочки", len(wi.findChildren(_T)) == 2 + 1 + 9, str(len(wi.findChildren(_T))))
    check("Интернет: цветът на сайта се прилага", any(t.bg == "#80FF0000" for t in wi.findChildren(_T)))
    cfg.reset(); cfg["behavior"]["hover_delay_ms"] = 0
    ov.rebuild()
    from radialwheel.kbpanel import OskKey
    wk, hk = ov.dims["keyboard"]
    kb = BUILDERS["keyboard"](ov.ctx, wk, hk); kb.show()
    check("клавиатура: височината е над два компактни панела", hk > 2 * kb.Hc, f"{hk} vs {kb.Hc}")
    import radialwheel.kbpanel as _kbm
    _kbm.QCursor = type("QC", (), {"pos": staticmethod(lambda: kb.mapToGlobal(kb.rect().center()))})
    kb.eventFilter(kb.frames[1], QEvent(QEvent.Enter))
    t0 = _t3.time()
    while _t3.time() - t0 < 0.8:
        app.processEvents(); _t3.sleep(0.01)
    check("посочване разгъва панела (t=1)", kb.cur == 1 and kb.t > 0.99, f"{kb.cur} {kb.t}")
    keys = kb.findChildren(OskKey)
    check("компактна клавиатура: 61 клавиша", len(keys) == 61, str(len(keys)))
    kk = [k for k in keys if k.vk == 0x41][0]
    check("клавишите са приблизително квадратни", abs(kk.width() - kk.height()) <= 4, f"{kk.width()}x{kk.height()}")
    sentk = []
    actions.winapi.send_keys = lambda v: sentk.append(list(v))
    kk.on_click(kk)
    sh = [k for k in keys if k.vk == 0xA0][0]
    sh.on_click(sh)
    kk.on_click(kk)
    check("клавиш A и Shift+A (залепващ Shift)", sentk == [[0x41], [0xA0, 0x41]], str(sentk))
    kb.collapse()
    t0 = _t3.time()
    while _t3.time() - t0 < 0.8:
        app.processEvents(); _t3.sleep(0.01)
    check("свиване връща компактния вид", kb.cur == -1 and kb.t == 0.0)

    # 7d. обновяване от zip
    import tempfile, zipfile, shutil as _sh
    from radialwheel import updater, __version__
    td = tempfile.mkdtemp()
    zp = os.path.join(td, "new.zip")
    src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with zipfile.ZipFile(zp, "w") as z:
        for root, _d, files in os.walk(os.path.join(src, "app")):
            if "__pycache__" in root:
                continue
            for f in files:
                full = os.path.join(root, f)
                arc = "RadialWheel/" + os.path.relpath(full, src).replace(os.sep, "/")
                if arc.endswith("app/radialwheel/__init__.py"):
                    z.writestr(arc, open(full, encoding="utf-8").read().replace(__version__, "9.9.9", 1))
                else:
                    z.write(full, arc)
    prefix, ver = updater.inspect_zip(zp)
    check("zip: открива app/ и версията", prefix == "RadialWheel/app/" and ver == "9.9.9", f"{prefix} {ver}")
    st = updater.stage(zp, prefix)
    check("zip: разархивира app/", (st / "main.py").exists() and (st / "radialwheel" / "updater.py").exists())
    _sh.rmtree(st, ignore_errors=True)
    bad = os.path.join(td, "bad.zip")
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("readme.txt", "x")
    try:
        updater.inspect_zip(bad)
        check("невалиден zip се отхвърля", False)
    except updater.UpdateError:
        check("невалиден zip се отхвърля", True)
    check("версии се сравняват", updater.parse_version("1.10.0") > updater.parse_version("1.9.2"))

    # 8. диалог за настройки
    from radialwheel.settings_dialog import PAGES, SettingsDialog
    ctl.apply_config = lambda: None
    ctl.reload_triggers = lambda: (True, "")
    ctl.set_autostart = lambda v: None
    dlg = SettingsDialog(ctl)
    for i in range(len(PAGES)):
        dlg.open_page(i)
        app.processEvents()
    check("диалогът за настройки има всички страници", dlg.stack.count() == len(PAGES) == 16)
    # редакция на папка и програма през диалога
    from PySide6.QtWidgets import QLineEdit, QScrollArea
    dlg.open_page("folders")
    ed = dlg.stack.widget(PAGES.index("folders")).widget().findChildren(QLineEdit)[1]
    ed.setText("D:\\Work\\Docs")
    ed.editingFinished.emit()
    check("папка се записва от настройките", cfg["folders"][0]["path"].replace("/", "\\") == "D:\\Work\\Docs")
    dlg.open_page("shortcuts")
    eds = dlg.stack.widget(PAGES.index("shortcuts")).widget().findChildren(QLineEdit)
    eds[0].setText("Ctrl+Shift+Esc")
    eds[1].setText("Ctrl+Foo")
    eds[0].editingFinished.emit()
    check("валидна комбинация се записва, невалидната – не",
          cfg["quick_shortcuts"][0][0]["keys"] == "Ctrl+Shift+Esc" and all("Foo" not in i["keys"] for r in cfg["quick_shortcuts"] for i in r))
    # зъбно колело в панелите
    from radialwheel.widgets import Frame as _F
    ov.hide(); ov.popup()
    got = []
    ov.act.open_settings = lambda p: got.append(p)
    for idx, sid in enumerate(cfg["sector_order"]):
        ov.wheel.reset_state(); ov.wheel._armed = True
        a = math.radians(idx * 45)
        ov.wheel.track(QPointF(ov.wheel.c.x() + r * math.sin(a), ov.wheel.c.y() - r * math.cos(a)))
        gl = [f for f in ov.panel.findChildren(_F) + ([ov.panel] if isinstance(ov.panel, _F) else []) if f.has_gear]
        if sid == "settings":
            check("панелът Настройки няма зъбно колело", not gl)
        else:
            check(f"зъбно колело в панел {sid}", len(gl) == 1)
            gl[0].settingsRequested.emit()
    check("зъбните колела отварят правилните страници", got == ["shortcuts", "folders", "functions", "favorites", "sounds", "internet", "programs"], str(got))

    print("\nПровалени:", failed if failed else "няма")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
