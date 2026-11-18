"""Геометрия на решетката от плочки във всеки панел (брой на ред, редове, размери)."""
import math

from .config import cfg

DEF_TILE_W, DEF_TILE_H = 96, 82
GRID_PANELS = ["folders", "programs", "favorites", "system", "settings"]
LIST_PANELS = {"folders", "programs", "favorites"}          # динамичен брой слотове


def panel_count(sid: str) -> int:
    return max(1, len(cfg[sid])) if sid in LIST_PANELS else 8


def grid_params(sid: str, n: int, s: float):
    """Връща речник с cols, rows, tile_w, tile_h, gap, pad, sh, header, W, H (при мащаб s)."""
    g = cfg["grid"].get(sid, {})
    n = max(1, n)
    mode, val = g.get("mode", "single"), max(1, int(g.get("value", 4)))
    if mode == "per_row":
        cols = min(val, n)
    elif mode == "rows":
        cols = math.ceil(n / min(val, n))
    else:
        cols = n
    rows = math.ceil(n / cols)
    tile_w = round((g.get("tile_w") or DEF_TILE_W) * s)
    tile_h = round((g.get("tile_h") or DEF_TILE_H) * s)
    gap, pad, sh, header = round(6 * s), round(8 * s), round(6 * s), round(26 * s)
    auto_w = cols * tile_w + (cols - 1) * gap + 2 * pad + 2 * sh
    if g.get("panel_w"):
        W = round(g["panel_w"] * s) + 2 * sh
    else:
        W = max(auto_w, round(320 * s) + 2 * sh)
    H = 2 * sh + header + 2 * pad + rows * tile_h + (rows - 1) * gap
    return dict(cols=cols, rows=rows, tile_w=tile_w, tile_h=tile_h, gap=gap, pad=pad, sh=sh, header=header, W=W, H=H,
                icon=round(g.get("icon", 0) * s), font=g.get("font", 0) * s)
