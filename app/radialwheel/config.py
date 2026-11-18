"""Конфигурация (config.json) – лесно четим, с бекъп/експорт/ръчно редактиране."""
import copy
import json
import logging
import os
import shutil
from pathlib import Path

from .paths import CONFIG_FILE

log = logging.getLogger(__name__)

SECTOR_IDS = ["keyboard", "folders", "system", "favorites", "sound", "internet", "settings", "programs"]

DEFAULTS = {
    "version": 1,
    "language": "en",
    "hotkey": {"enabled": True, "ctrl": True, "alt": True, "shift": False, "win": False, "key": "Space"},
    "mouse_trigger": "none",          # none | middle | xbutton1 | xbutton2
    "appearance": {
        "opacity": 1.0, "scale": 1.0, "panel_scale": 1.0, "animations": True,
        "theme": "dark",               # dark | light | custom
        "accent": "#6897E8",
    },
    "behavior": {
        "open_mode": "hover",          # hover | click
        "hover_delay_ms": 80,
        "autohide_ms": 0,              # 0 = изключено
        "autofocus_search": True,
        "confirm_power": True,
    },
    "sounds": True,
    "sector_order": list(SECTOR_IDS),  # по часовниковата стрелка, започва от 12:00
    "custom_icons": {},                # sector_id -> път до .png/.svg/.ico
    "folders": [
        {"id": "documents", "path": "%USERPROFILE%\\Documents"},
        {"id": "pictures", "path": "%USERPROFILE%\\Pictures"},
        {"id": "music", "path": "%USERPROFILE%\\Music"},
        {"id": "videos", "path": "%USERPROFILE%\\Videos"},
        {"id": "projects", "path": "%USERPROFILE%\\Projects"},
        {"id": "downloads", "path": "%USERPROFILE%\\Downloads"},
        {"id": "archive", "path": "%USERPROFILE%\\Archive"},
        {"id": "system", "path": "C:\\"},
    ],
    # path == "" -> вградено поведение по подразбиране
    "programs": [{"id": i, "path": ""} for i in
                 ("browser", "editor", "player", "calculator", "graphics", "mail", "games", "notes")],
    "browsers": [{"id": i, "path": ""} for i in ("chrome", "firefox", "edge", "opera")],
    "sites": [
        {"id": "favorites", "url": "https://www.google.com"},
        {"id": "news", "url": "https://news.google.com"},
        {"id": "mail", "url": "https://mail.google.com"},
        {"id": "social", "url": "https://www.facebook.com"},
    ],
    "bookmarks_folder": "%USERPROFILE%\\Favorites",
    "favorites": [{"id": "custom", "path": "", "label": ""} for _ in range(8)],
    # решетка на плочките: mode = single | per_row | rows ; 0 при размерите = автоматично
    "grid": {sid: {"mode": "single", "value": 4, "tile_w": 0, "tile_h": 0, "icon": 0, "font": 0, "panel_w": 0, "bg": ""}
             for sid in ("folders", "programs", "favorites", "system", "settings")},
    "quick_shortcuts": [
        [{"keys": "Shift+Win+S", "tip": "Screenshot"}, {"keys": "Ctrl+C", "tip": "Copy"}, {"keys": "Ctrl+V", "tip": "Paste"}],
        [{"keys": "Alt+Left", "tip": "Back"}, {"keys": "Alt+Right", "tip": "Forward"},
         {"keys": "Ctrl+Z", "tip": "Undo"}],
    ],
}


def _merge(base, over):
    """Рекурсивно слива `over` върху копие на `base`; невалидни типове се игнорират."""
    out = copy.deepcopy(base)
    if not isinstance(over, dict):
        return out
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        elif k in out and type(out[k]) is not type(v) and not (
                isinstance(out[k], (int, float)) and isinstance(v, (int, float)) and not isinstance(v, bool)):
            continue
        else:
            out[k] = v
    return out


class Config:
    def __init__(self):
        self.data = copy.deepcopy(DEFAULTS)

    # ---------------------------------------------------------------- IO
    def load(self):
        f = Path(CONFIG_FILE())
        if f.exists():
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                self.data = _merge(DEFAULTS, raw)
            except Exception:
                log.exception("config.json е повреден – запазвам копие и зареждам стойностите по подразбиране")
                try:
                    shutil.copy2(f, f.with_suffix(".broken.json"))
                except Exception:
                    log.exception("Неуспешно копиране на повредения config")
                self.data = copy.deepcopy(DEFAULTS)
        self._sanitize()
        if not f.exists():
            self.save()

    def save(self):
        f = Path(CONFIG_FILE())
        tmp = f.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, f)
        except Exception:
            log.exception("Неуспешен запис на config.json")

    def reset(self):
        self.data = copy.deepcopy(DEFAULTS)
        self.save()

    def _sanitize(self):
        order = self.data.get("sector_order", [])
        if sorted(order) != sorted(SECTOR_IDS):
            self.data["sector_order"] = list(SECTOR_IDS)
        a = self.data["appearance"]
        a["opacity"] = min(1.0, max(0.3, float(a["opacity"])))
        a["scale"] = min(2.0, max(0.6, float(a["scale"])))
        a["panel_scale"] = min(1.5, max(0.5, float(a["panel_scale"])))
        for key in ("folders", "programs", "favorites"):
            self.data[key] = [e for e in self.data[key] if isinstance(e, dict)][:60]
            for e in self.data[key]:
                e.setdefault("id", "custom")
                e.setdefault("path", "")
        for g in self.data["grid"].values():
            g["value"] = max(1, int(g["value"]))
            for k in ("tile_w", "tile_h", "icon", "font", "panel_w"):
                g[k] = max(0, int(g[k]))
            g["bg"] = g.get("bg") if isinstance(g.get("bg"), str) else ""

    # ---------------------------------------------------------------- достъп
    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v


cfg = Config()
