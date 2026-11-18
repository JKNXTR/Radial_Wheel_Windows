"""Цветови теми (спецификация т. 2.1)."""
from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class Theme:
    name: str
    wheel_top: str
    wheel_bottom: str
    wheel_border: str
    sector_line: str
    active_top: str
    active_bottom: str
    active_border: str
    center_top: str
    center_bottom: str
    delete_top: str = "#C82828"
    delete_bottom: str = "#A81C1C"
    panel_top: str = "#3A3A3A"
    panel_bottom: str = "#262626"
    panel_border: str = "#141414"
    header_bg: str = "#222222"
    tile_bg: str = "#2A2A2A"
    tile_border: str = "#161616"
    tile_hover: str = "#383838"
    text: str = "#ECE6D4"
    keycap_top: str = "#E6E6E6"
    keycap_bottom: str = "#CDCDCD"
    keycap_border: str = "#3A3A3A"
    keycap_text: str = "#111111"
    input_bg: str = "#FFFFFF"
    input_text: str = "#111111"
    popup_bg: str = "#1E1E1E"


DARK = Theme(
    name="dark",
    wheel_top="#232323", wheel_bottom="#191919", wheel_border="#111111", sector_line="#111111",
    active_top="#6897E8", active_bottom="#4A76C5", active_border="#9BBDF9",
    center_top="#333333", center_bottom="#2B2B2B",
)

LIGHT = Theme(
    name="light",
    wheel_top="#F2F2F2", wheel_bottom="#DCDCDC", wheel_border="#9A9A9A", sector_line="#A8A8A8",
    active_top="#6897E8", active_bottom="#4A76C5", active_border="#9BBDF9",
    center_top="#FFFFFF", center_bottom="#E4E4E4",
    panel_top="#F4F4F4", panel_bottom="#DEDEDE", panel_border="#9A9A9A", header_bg="#CFCFCF",
    tile_bg="#FAFAFA", tile_border="#B5B5B5", tile_hover="#E8EEFA", text="#1D1D1D",
    keycap_top="#FFFFFF", keycap_bottom="#E2E2E2", keycap_border="#777777",
    popup_bg="#F4F4F4",
)


def _shade(hex_color: str, factor: float) -> str:
    c = QColor(hex_color)
    h, s, v, a = c.getHsv()
    v = max(0, min(255, int(v * factor)))
    return QColor.fromHsv(h, s, v, a).name()


def build_theme(kind: str, accent: str) -> Theme:
    import copy
    t = copy.deepcopy(LIGHT if kind == "light" else DARK)
    if kind == "custom" or accent.lower() != "#6897e8":
        base = QColor(accent)
        if base.isValid():
            t.active_top = base.name()
            t.active_bottom = _shade(base.name(), 0.84)
            t.active_border = _shade(base.name(), 1.25) if base.value() < 215 else "#FFFFFF"
    return t
