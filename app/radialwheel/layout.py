"""Геометрия на решетката от плочки във всеки панел (брой на ред, редове, размери)."""
import math

from .config import cfg

DEF_TILE_W, DEF_TILE_H = 96, 82
PANEL_H = 124                 # височина на компактен панел при мащаб 100 %
GRID_PANELS = ["folders", "programs", "favorites", "system", "settings"]
LIST_PANELS = {"folders", "programs", "favorites"}          # динамичен брой слотове


def panel_count(sid: str) -> int:
    return max(1, len(cfg[sid])) if sid in LIST_PANELS else 8


def cols_rows(sid: str, n: int):
    g = cfg["grid"].get(sid, {})
    n = max(1, n)
    mode, val = g.get("mode", "single"), max(1, int(g.get("value", 4)))
    if mode == "per_row":
        cols = min(val, n)
    elif mode == "rows":
        cols = math.ceil(n / min(val, n))
    else:
        cols = n
    return cols, math.ceil(n / cols)


def internet_geom(s: float, base_w: int, base_h: int):
    """Размери на панела „Интернет“ при мащаб s: ширината и височината растат с броя колони/редове на сайтовете."""
    from .config import cfg as _c
    sh, gap = round(6 * s), round(8 * s)
    n_sites = 1 + len(_c["sites"])                      # + папката с отметки
    cols, rows = cols_rows("internet", n_sites)
    tile_w, tile_h = round(66 * s), round(62 * s)
    nb = max(1, len(_c["browsers"]))
    bw = nb * tile_w + (nb - 1) * round(5 * s) + round(22 * s)
    gw = round(250 * s)
    sw = cols * tile_w + (cols - 1) * round(5 * s) + round(22 * s)
    inner = bw + gw + sw + 2 * gap
    W = max(base_w, inner + 2 * sh + 2 * round(8 * s))
    H = base_h + (rows - 1) * (tile_h + round(5 * s))
    return dict(W=W, H=H, bw=bw, gw=gw, cols=cols, rows=rows, tile_w=tile_w, tile_h=tile_h, gap=gap)


def grid_params(sid: str, n: int, s: float):
    """Връща речник с cols, rows, tile_w, tile_h, gap, pad, sh, header, W, H (при мащаб s)."""
    g = cfg["grid"].get(sid, {})
    n = max(1, n)
    cols, rows = cols_rows(sid, n)
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


def kbd_dims(s: float, base_w: int):
    """Размери на клавиатурния панел: 3 компактни панела (ширина base_w) или един разгънат с квадратни клавиши (15 × 5 единици)."""
    sh, pad, header = round(6 * s), round(8 * s), round(26 * s)
    inner_w = base_w - 2 * sh - 2 * pad
    u = inner_w / 15.0
    H = 2 * sh + header + 2 * pad + round(5 * u)
    Hc = round(PANEL_H * s) + 2 * sh
    return dict(W=base_w, H=H, Hc=Hc, u=u, inner_w=inner_w, inner_h=round(5 * u))
