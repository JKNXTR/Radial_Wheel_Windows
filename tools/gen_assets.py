"""Генератор на всички икони (SVG), app.ico/app.png и звука tick.wav.

Стартиране:  python tools/gen_assets.py
Резултат:    app/assets/icons/*.svg, app/assets/app.ico, app/assets/app.png,
             app/assets/sounds/tick.wav

Иконите са оригинални векторни рисунки (не са копия на чужди лога).
Могат да се заменят с каквито и да е .svg/.png/.ico от Настройки -> Икони.
"""
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "app" / "assets" / "icons"
SOUNDS = ROOT / "app" / "assets" / "sounds"
ICONS.mkdir(parents=True, exist_ok=True)
SOUNDS.mkdir(parents=True, exist_ok=True)

YEL, YEL_D, YEL_L = "#F6D365", "#D9A526", "#FBE79A"
BLUE, BLUE_D, BLUE_L = "#4A76C5", "#2F528F", "#9BBDF9"
GRAY, GRAY_D, GRAY_L = "#B8BBC6", "#6B6F80", "#E3E5EC"
DARK = "#2B2F3A"


def svg(body, defs=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
            f"<defs>{defs}</defs>{body}</svg>")


def lin(id_, c1, c2, vertical=True):
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>')


def gear(cx, cy, ro, ri, teeth, hole, fill, stroke):
    pts = []
    n = teeth * 4
    for i in range(n):
        a = 2 * math.pi * i / n
        r = ro if (i % 4) in (0, 1) else ri
        pts.append(f"{cx + r * math.cos(a):.2f},{cy + r * math.sin(a):.2f}")
    return (f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{stroke}" stroke-width="1" '
            f'stroke-linejoin="round"/><circle cx="{cx}" cy="{cy}" r="{hole}" fill="{DARK}" opacity="0.9"/>')


def star(cx, cy, ro, ri, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = ro if i % 2 == 0 else ri
        pts.append(f"{cx + r * math.cos(a):.2f},{cy + r * math.sin(a):.2f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="#8a6a10" stroke-width="1" stroke-linejoin="round"/>'


def folder(overlay=""):
    defs = lin("fg", YEL_L, YEL) + lin("fb", YEL, YEL_D)
    body = ('<path d="M5 13h18l5 6h30a2 2 0 0 1 2 2v32a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3z" fill="url(#fb)" stroke="#B8861B" stroke-width="1.2"/>'
            '<path d="M5 24h54v29a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3z" fill="url(#fg)" stroke="#B8861B" stroke-width="1.2"/>')
    return svg(body + overlay, defs)


def speaker(waves=True, color="#C8CBD6", wave_color="#6C94EA", muted=False):
    b = (f'<path d="M8 25h10l12-10v34L18 39H8z" fill="{color}" stroke="{GRAY_D}" stroke-width="1.5" stroke-linejoin="round"/>')
    if muted:
        b += f'<path d="M38 26l14 14M52 26L38 40" stroke="#D84848" stroke-width="4" stroke-linecap="round"/>'
    elif waves:
        for r, o in ((8, 1), (15, .9), (22, .8)):
            b += (f'<path d="M36 {32 - r}a{r + 2} {r + 2} 0 0 1 0 {2 * r}" fill="none" stroke="{wave_color}" '
                  f'stroke-width="3.2" stroke-linecap="round" opacity="{o}"/>')
    return svg(b)


def window(hdr=BLUE, inner=""):
    defs = lin("wb", "#F2F4FA", "#C9CEDC") + lin("wh", hdr, BLUE_D)
    return svg('<rect x="6" y="9" width="52" height="46" rx="4" fill="url(#wb)" stroke="#5B6074" stroke-width="1.5"/>'
               '<path d="M6 13a4 4 0 0 1 4-4h44a4 4 0 0 1 4 4v6H6z" fill="url(#wh)"/>' + inner, defs)


def keyboard(color="#D5D8E2"):
    b = f'<rect x="3" y="14" width="58" height="36" rx="4" fill="{color}" stroke="{GRAY_D}" stroke-width="1.6"/>'
    for r in range(3):
        for c in range(8 if r < 2 else 6):
            x = 8 + c * 6.4 + (0 if r < 2 else 6.4)
            b += f'<rect x="{x:.1f}" y="{19 + r * 8}" width="4.6" height="5" rx="1" fill="#7C8196"/>'
    b += f'<rect x="19" y="43" width="26" height="4" rx="1.4" fill="#7C8196"/>'
    return svg(b)


def globe(color=BLUE_L):
    s = f'stroke="{color}" stroke-width="2.2" fill="none"'
    return svg(f'<circle cx="32" cy="32" r="24" {s}/><ellipse cx="32" cy="32" rx="10" ry="24" {s}/>'
               f'<ellipse cx="32" cy="32" rx="19" ry="24" {s} opacity=".6"/>'
               f'<path d="M8 32h48M12 20h40M12 44h40" {s}/><path d="M32 8v48" {s}/>')


ICON_SET = {}


def add(name, content):
    ICON_SET[name] = content


# ---------------------------------------------------------------- сектори
add("sector_keyboard", keyboard())
add("sector_folders", folder())
add("sector_windows", svg(
    '<g transform="rotate(-8 32 32)">'
    '<rect x="8" y="9" width="23" height="23" rx="3" fill="#F25B3A"/>'
    '<rect x="33" y="7" width="23" height="23" rx="3" fill="#7DBB2A"/>'
    '<rect x="8" y="34" width="23" height="23" rx="3" fill="#2E9BE8"/>'
    '<rect x="33" y="32" width="23" height="23" rx="3" fill="#F7B21B"/></g>'))
add("sector_favorites", folder(star(32, 41, 11, 4.6, "#6B5313")))
add("sector_sound", speaker())
add("sector_internet", globe())
add("sector_settings", svg(
    f'<rect x="4" y="6" width="56" height="52" rx="4" fill="#D6D8E0" stroke="#7B7F90" stroke-width="1.5"/>'
    + gear(26, 38, 15, 11.5, 8, 4.5, "#5B6074", "#2f3340")
    + gear(46, 20, 10, 7.6, 7, 3.2, "#5B6074", "#2f3340")))
add("sector_programs", window(inner=(
    '<rect x="11" y="25" width="16" height="10" rx="1.5" fill="#4A76C5"/>'
    '<rect x="31" y="25" width="22" height="3" fill="#7C8196"/><rect x="31" y="31" width="22" height="3" fill="#7C8196"/>'
    '<rect x="11" y="39" width="16" height="10" rx="1.5" fill="#7C8196"/>'
    '<rect x="31" y="39" width="22" height="3" fill="#7C8196"/><rect x="31" y="45" width="22" height="3" fill="#7C8196"/>')))

# ---------------------------------------------------------------- папки
add("folder_documents", folder('<rect x="22" y="28" width="20" height="25" rx="1.5" fill="#fff" stroke="#9aa" />'
                               '<path d="M26 34h12M26 39h12M26 44h8" stroke="#8b93a5" stroke-width="2"/>'))
add("folder_pictures", folder('<rect x="16" y="29" width="32" height="23" rx="2" fill="#bfe0ff" stroke="#3E6FB5" stroke-width="2"/>'
                              '<path d="M16 50l10-11 7 7 6-5 9 9z" fill="#3E7A4A"/><circle cx="40" cy="35" r="3" fill="#fff"/>'))
add("folder_music", folder('<path d="M27 49a4.5 4 0 1 0 .01 0zM41 46a4.5 4 0 1 0 .01 0z" fill="#2F528F"/>'
                           '<path d="M31 49V30l14-4v19" fill="none" stroke="#2F528F" stroke-width="3"/>'
                           '<path d="M31 30l14-4v6l-14 4z" fill="#2F528F"/>'))
add("folder_videos", folder('<rect x="16" y="28" width="32" height="24" rx="2" fill="#3a3f4d"/>'
                            '<rect x="23" y="31" width="18" height="18" fill="#9aa3b8"/>'
                            + "".join(f'<rect x="{x}" y="{y}" width="3" height="3" fill="#e8e8e8"/>'
                                      for x in (18.5, 42.5) for y in (31, 37, 43, 48))))
add("folder_projects", folder())
add("folder_downloads", folder('<path d="M32 28v16" stroke="#2E6FD0" stroke-width="6" stroke-linecap="round"/>'
                               '<path d="M21 40l11 12 11-12z" fill="#2E6FD0"/>'))
add("folder_archive", folder('<rect x="28" y="24" width="8" height="30" fill="#8f7220" opacity=".55"/>'
                             + "".join(f'<rect x="{30 + (i % 2) * 2}" y="{27 + i * 5}" width="4" height="3" fill="#fff"/>'
                                       for i in range(5))))
add("folder_system", folder(gear(32, 41, 11, 8.5, 8, 3.8, "#5B6074", "#2f3340")))
add("folder_generic", folder())

# ---------------------------------------------------------------- програми
add("app_browser", svg(
    '<circle cx="32" cy="32" r="25" fill="#F28C28" stroke="#B85F0E" stroke-width="2"/>'
    '<circle cx="32" cy="32" r="15" fill="#FFE6C2"/>'
    f'<path d="M17 32h30M32 17v30" stroke="#B85F0E" stroke-width="2"/><ellipse cx="32" cy="32" rx="7" ry="15" fill="none" stroke="#B85F0E" stroke-width="2"/>'))
add("app_editor", svg(
    '<rect x="11" y="6" width="38" height="50" rx="3" fill="#fff" stroke="#8b93a5" stroke-width="2"/>'
    '<path d="M17 16h26M17 23h26M17 30h26M17 37h18" stroke="#9aa3b8" stroke-width="2.4"/>'
    '<path d="M36 52l4-12 18-18 8 8-18 18z" fill="#F6B23B" stroke="#8a5a10" stroke-width="1.5" transform="translate(-6 2) scale(.9)"/>'
    '<path d="M31 50l-1 7 7-2z" fill="#444"/>'))
add("app_player", svg('<circle cx="32" cy="32" r="26" fill="#F28C28" stroke="#B85F0E" stroke-width="2"/>'
                      '<circle cx="32" cy="32" r="20" fill="none" stroke="#fff" stroke-width="2" opacity=".6"/>'
                      '<path d="M26 20v24l20-12z" fill="#fff"/>'))
add("app_calculator", svg(
    '<rect x="12" y="5" width="40" height="54" rx="4" fill="#A9AEBB" stroke="#5B6074" stroke-width="2"/>'
    '<rect x="17" y="10" width="30" height="12" rx="1.5" fill="#B5DDB2" stroke="#4d6b4a"/>'
    + "".join(f'<rect x="{17 + c * 8.6}" y="{27 + r * 8.6}" width="6.4" height="6.4" rx="1.2" fill="{"#F6A23B" if c == 3 else "#6B6F80"}"/>'
              for r in range(4) for c in range(4))))
add("app_graphics", svg(
    '<rect x="6" y="9" width="42" height="34" rx="3" fill="#cfe6ff" stroke="#5B6074" stroke-width="2"/>'
    '<path d="M6 38l12-12 9 9 7-6 14 14v-4H6z" fill="#4C9A5B"/><circle cx="38" cy="19" r="4" fill="#FFD84D"/>'
    '<path d="M30 54l22-30 6 5-22 30z" fill="#E1A33A" stroke="#7c5410" stroke-width="1.5"/>'
    '<path d="M30 54l-3 7 8-3z" fill="#333"/>'))
add("app_mail", svg(
    '<path d="M6 28l26-18 26 18v26a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3z" fill="#E3EAF8" stroke="#4A76C5" stroke-width="2"/>'
    '<rect x="14" y="19" width="36" height="22" fill="#fff" stroke="#c0c8da"/><path d="M19 25h26M19 31h26M19 37h16" stroke="#aab4cc" stroke-width="2"/>'
    '<path d="M6 28l26 18 26-18v26a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3z" fill="#F4F7FD" stroke="#4A76C5" stroke-width="2"/>'))
add("app_games", svg(
    '<path d="M14 20h36c6 0 10 8 12 20 1 6-3 10-8 8l-9-5H19l-9 5c-5 2-9-2-8-8 2-12 6-20 12-20z" fill="#7B7F8C" stroke="#3b3f4a" stroke-width="2" stroke-linejoin="round"/>'
    '<path d="M18 28v10M13 33h10" stroke="#222" stroke-width="3.4" stroke-linecap="round"/>'
    '<circle cx="43" cy="29" r="2.6" fill="#E85D5D"/><circle cx="48" cy="34" r="2.6" fill="#4A9BE8"/>'
    '<circle cx="38" cy="34" r="2.6" fill="#F7C531"/><circle cx="43" cy="39" r="2.6" fill="#59B86A"/>'))
add("app_notes", svg(
    '<path d="M10 6h44v38l-14 14H10z" fill="#F7E36B" stroke="#B49A18" stroke-width="2" stroke-linejoin="round"/>'
    '<path d="M54 44H40v14z" fill="#D9C24A" stroke="#B49A18" stroke-width="2" stroke-linejoin="round"/>'
    '<path d="M19 30l9 9 17-20" fill="none" stroke="#2E9B4A" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M16 12h26" stroke="#B49A18" stroke-width="2"/>'))

# ---------------------------------------------------------------- настройки на колелото
add("set_view", svg('<path d="M3 32C12 18 22 12 32 12s20 6 29 20c-9 14-19 20-29 20S12 46 3 32z" fill="#fff" stroke="#4A5170" stroke-width="2.5"/>'
                    '<circle cx="32" cy="32" r="12" fill="#4A76C5"/><circle cx="32" cy="32" r="5.5" fill="#111"/><circle cx="28" cy="28" r="2.5" fill="#fff"/>'
                    '<circle cx="50" cy="48" r="4.5" fill="#E8533A"/><circle cx="58" cy="40" r="4" fill="#59B86A"/><circle cx="44" cy="55" r="4" fill="#F7C531"/>'))
add("set_layout", svg("".join(
    f'<rect x="{6 + c * 18}" y="{6 + r * 18}" width="14" height="14" rx="1.5" fill="{"#4A76C5" if (r, c) in ((0, 0), (0, 1)) else ("#E3E5EC" if (r, c) == (1, 1) else "#8C90A0")}"/>'
    for r in range(3) for c in range(3))))
add("set_icons", folder('<path d="M30 24h12v-6l10 9-10 9v-6H30z" fill="#4CB05B" transform="translate(4 -1)"/>'
                        '<rect x="14" y="34" width="26" height="16" rx="2" fill="#C9CCD6" stroke="#6B6F80"/>'
                        '<path d="M18 40h18M18 45h10" stroke="#6B6F80" stroke-width="2"/>'))
add("set_functions", svg(gear(28, 32, 22, 17, 8, 8, "#8E93A6", "#3b4050")
                         + '<circle cx="46" cy="44" r="8" fill="#F2C94C" stroke="#8a6a10" stroke-width="2"/>'
                           '<circle cx="46" cy="44" r="3" fill="#2B2F3A"/><path d="M52 50l8 8" stroke="#8a6a10" stroke-width="5" stroke-linecap="round"/>'))
add("set_themes", svg('<path d="M14 54l24-30 8 7-26 29z" fill="#C98B3E" stroke="#7a4f14" stroke-width="2" transform="translate(-2 4)"/>'
                      '<path d="M38 24l16-18 6 6-14 20z" fill="#444" stroke="#111" stroke-width="2"/>'
                      '<circle cx="46" cy="44" r="13" fill="#fff" stroke="#333" stroke-width="2"/>'
                      '<path d="M46 31a13 13 0 0 1 0 26z" fill="#1c1c1c"/>'))
add("set_hotkeys", svg('<rect x="6" y="20" width="22" height="32" rx="3" fill="#E3E5EC" stroke="#6B6F80" stroke-width="2"/>'
                       '<rect x="10" y="30" width="14" height="5" rx="1.5" fill="#fff" stroke="#6B6F80"/>'
                       '<rect x="34" y="14" width="24" height="38" rx="12" fill="#D6D9E3" stroke="#6B6F80" stroke-width="2"/>'
                       '<path d="M46 14v16M34 30h24" stroke="#6B6F80" stroke-width="2"/><rect x="43.5" y="18" width="5" height="9" rx="2.5" fill="#4A76C5"/>'))
add("set_sounds", svg('<path d="M6 25h10l12-10v34L16 39H6z" fill="#C8CBD6" stroke="#6B6F80" stroke-width="1.5" stroke-linejoin="round"/>'
                      '<path d="M44 12v28" stroke="#4A76C5" stroke-width="4.5" stroke-linecap="round"/>'
                      '<ellipse cx="38" cy="42" rx="7" ry="5.5" fill="#4A76C5"/><path d="M44 12c6 0 10 4 10 10" stroke="#4A76C5" stroke-width="4.5" fill="none" stroke-linecap="round"/>'))
add("set_update", svg('<path d="M32 8v32" stroke="#2E9E5B" stroke-width="8" stroke-linecap="round"/>'
                      '<path d="M16 28l16 16 16-16" fill="none" stroke="#2E9E5B" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
                      '<path d="M12 54h40" stroke="#2E9E5B" stroke-width="6" stroke-linecap="round"/>'))
add("set_reset", svg('<path d="M32 10a22 22 0 1 1-20.5 14" fill="none" stroke="#2E6FD0" stroke-width="8" stroke-linecap="round"/>'
                     '<path d="M32 -2v24L12 10z" fill="#2E6FD0" transform="translate(-9 4) rotate(-15 20 10)"/>'))

# ---------------------------------------------------------------- браузъри / сайтове
for key, color, letter in (("chrome", "#4CAF50", "C"), ("firefox", "#F28C28", "F"), ("edge", "#2E86DE", "E"), ("opera", "#D9342B", "O")):
    add(f"br_{key}", svg(f'<circle cx="32" cy="32" r="29" fill="{color}" stroke="#222" stroke-opacity=".35" stroke-width="2"/>'
                         f'<circle cx="32" cy="32" r="17" fill="#fff"/>'
                         f'<text x="32" y="41" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="700" text-anchor="middle" fill="{color}">{letter}</text>'))
add("site_folder", folder())
add("site_favorites", svg(star(32, 33, 27, 11.5, "#F7C531")))
add("site_news", svg('<rect x="6" y="10" width="52" height="44" rx="3" fill="#fff" stroke="#3E57A8" stroke-width="2.5"/>'
                     '<rect x="11" y="15" width="18" height="14" fill="#3E57A8"/><path d="M33 17h20M33 23h20M33 29h20M11 36h42M11 42h42M11 48h30" stroke="#8d97b8" stroke-width="2.6"/>'))
add("site_mail", svg('<rect x="5" y="14" width="54" height="38" rx="3" fill="#F3F5FA" stroke="#8b93a5" stroke-width="2.5"/>'
                     '<path d="M6 16l26 20 26-20" fill="none" stroke="#8b93a5" stroke-width="2.5"/>'))
add("site_social", svg('<circle cx="24" cy="22" r="9" fill="#3E6FD0"/><path d="M6 52c0-12 8-18 18-18s18 6 18 18z" fill="#3E6FD0"/>'
                       '<circle cx="46" cy="25" r="7.5" fill="#8EB4F0"/><path d="M36 52c0-9 4-15 11-15 8 0 13 6 13 15z" fill="#8EB4F0"/>'))
add("google_g", svg('<text x="32" y="48" font-family="Segoe UI, Arial, sans-serif" font-size="46" font-weight="700" text-anchor="middle" fill="#4285F4">G</text>'
                    '<path d="M50 33h-18" stroke="#EA4335" stroke-width="0"/>'))
add("search", svg('<circle cx="27" cy="27" r="16" fill="#eef" stroke="#6B6F80" stroke-width="5"/><path d="M39 39l18 18" stroke="#6B6F80" stroke-width="7" stroke-linecap="round"/>'))

# ---------------------------------------------------------------- звук
add("speaker_big", speaker())
add("speaker_small", speaker(waves=True))
add("speaker_muted", speaker(muted=True))

# ---------------------------------------------------------------- системни команди
add("sys_start", ICON_SET["sector_windows"])
add("sys_taskmgr", svg('<rect x="5" y="9" width="54" height="46" rx="3" fill="#1E2430" stroke="#6B6F80" stroke-width="2"/>'
                       '<path d="M9 42l9-8 7 6 9-18 8 12 6-6 7 5" fill="none" stroke="#59E07A" stroke-width="3" stroke-linejoin="round"/>'
                       '<path d="M9 48h46" stroke="#3a4152" stroke-width="2"/>'))
add("sys_settings", svg(gear(32, 32, 26, 20, 8, 9, "#9AA0B4", "#3b4050")))
add("sys_lock", svg('<path d="M20 28v-8a12 12 0 0 1 24 0v8" fill="none" stroke="#9AA0B4" stroke-width="6"/>'
                    '<rect x="11" y="28" width="42" height="29" rx="5" fill="#F2C94C" stroke="#8a6a10" stroke-width="2"/>'
                    '<circle cx="32" cy="41" r="4.5" fill="#3a2e08"/><rect x="30.3" y="42" width="3.4" height="9" fill="#3a2e08"/>'))
add("sys_sleep", svg('<path d="M44 8a24 24 0 1 0 12 40A20 20 0 0 1 44 8z" fill="#F2D86B" stroke="#8a6a10" stroke-width="2.5" stroke-linejoin="round"/>'
                     '<path d="M40 10h10l-10 10h10M52 24h7l-7 7h7" fill="none" stroke="#9BBDF9" stroke-width="2.6" stroke-linejoin="round"/>'))
add("sys_restart", svg('<path d="M32 10a22 22 0 1 1-21 15" fill="none" stroke="#4A9BE8" stroke-width="7" stroke-linecap="round"/>'
                       '<path d="M32 0v22L14 11z" fill="#4A9BE8" transform="translate(-8 5)"/>'))
add("sys_shutdown", svg('<path d="M20 15a22 22 0 1 0 24 0" fill="none" stroke="#E8533A" stroke-width="7" stroke-linecap="round"/>'
                        '<path d="M32 6v24" stroke="#E8533A" stroke-width="7" stroke-linecap="round"/>'))
add("sys_run", svg('<rect x="5" y="14" width="54" height="36" rx="4" fill="#E3E5EC" stroke="#6B6F80" stroke-width="2"/>'
                   '<rect x="5" y="14" width="54" height="9" rx="4" fill="#4A76C5"/><rect x="10" y="30" width="44" height="11" rx="2" fill="#fff" stroke="#8b93a5"/>'
                   '<path d="M14 36h14" stroke="#4A76C5" stroke-width="2.4"/><path d="M42 52l10-8v16z" fill="#2E9B4A" transform="translate(0 -3)"/>'))

# ---------------------------------------------------------------- любими / клавиатура
add("fav_add", svg('<rect x="6" y="6" width="52" height="52" rx="8" fill="none" stroke="#7a7f92" stroke-width="3" stroke-dasharray="6 5"/>'
                   '<path d="M32 18v28M18 32h28" stroke="#9BBDF9" stroke-width="6" stroke-linecap="round"/>'))
add("fav_file", svg('<path d="M14 6h26l12 12v40H14z" fill="#fff" stroke="#8b93a5" stroke-width="2.5" stroke-linejoin="round"/>'
                    '<path d="M40 6v12h12" fill="#D8DCE8" stroke="#8b93a5" stroke-width="2.5" stroke-linejoin="round"/>'
                    '<path d="M21 28h22M21 35h22M21 42h14" stroke="#aab4cc" stroke-width="2.6"/>'))
add("kb_keyboard", keyboard("#E1E3EA"))
add("kb_osk", ICON_SET["kb_keyboard"])

add("arrow_down", svg('<path d="M10 20h44L32 46z" fill="#ECE6D4"/>'))

# ---------------------------------------------------------------- приложение
APP_SVG = svg(
    '<circle cx="32" cy="32" r="29" fill="#1A1A1A" stroke="#0c0c0c" stroke-width="2"/>'
    + "".join(
        f'<path d="M{32 + 10 * math.sin(math.radians(a)):.2f} {32 - 10 * math.cos(math.radians(a)):.2f}L{32 + 29 * math.sin(math.radians(a)):.2f} {32 - 29 * math.cos(math.radians(a)):.2f}" stroke="#444" stroke-width="1.6"/>'
        for a in range(22, 360, 45))
    + '<path d="M22.4 11.2A24 24 0 0 1 41.6 11.2L37.4 22.6A12 12 0 0 0 26.6 22.6z" fill="#5E8FE0"/>'
    '<circle cx="32" cy="32" r="10" fill="#3a3a3a" stroke="#555"/>')
add("app", APP_SVG)

# минималистичен вариант за системната област: контрастен и четим и на 16 px, на светла и тъмна лента
TRAY_SVG = svg(
    '<circle cx="32" cy="32" r="30" fill="#F2F2F2" stroke="#1A1A1A" stroke-width="2"/>'
    '<path d="M32 32L19.3 4.6A30 30 0 0 1 44.7 4.6z" fill="#4A76C5"/>'
    + "".join(
        f'<path d="M32 32L{32 + 31 * math.sin(math.radians(a)):.2f} {32 - 31 * math.cos(math.radians(a)):.2f}" stroke="#1A1A1A" stroke-width="4.2"/>'
        for a in range(22, 360, 45) if a != 22 and a != 67 or False)
    + '<path d="M32 32L19.3 4.6M32 32L44.7 4.6" stroke="#1A1A1A" stroke-width="4.2"/>'
    '<path d="M32 32L58.2 19.8" stroke="#1A1A1A" stroke-width="4.2"/>'
    '<circle cx="32" cy="32" r="12" fill="#1A1A1A"/><circle cx="32" cy="32" r="7" fill="#3A3A3A"/>')
add("tray", TRAY_SVG)


def main():
    for name, content in ICON_SET.items():
        (ICONS / f"{name}.svg").write_text(content, encoding="utf-8")
    print(f"SVG икони: {len(ICON_SET)}")

    # PNG / ICO през Qt (ако е наличен), иначе пропускаме
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QGuiApplication, QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
        _app = QGuiApplication([])
        renderer = QSvgRenderer(QByteArray(APP_SVG.encode()))
        sizes = [16, 24, 32, 48, 64, 128, 256]
        images = {}
        for s in sizes:
            img = QImage(s, s, QImage.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            renderer.render(p)
            p.end()
            images[s] = img
        images[256].save(str(ROOT / "app" / "assets" / "app.png"))
        tray_r = QSvgRenderer(QByteArray(TRAY_SVG.encode()))
        timg = QImage(256, 256, QImage.Format_ARGB32)
        timg.fill(0)
        tp = QPainter(timg)
        tp.setRenderHint(QPainter.Antialiasing)
        tray_r.render(tp)
        tp.end()
        timg.save(str(ROOT / "app" / "assets" / "tray.png"))
        try:
            from PIL import Image
            big = Image.open(ROOT / "app" / "assets" / "app.png").convert("RGBA")
            big.save(ROOT / "app" / "assets" / "app.ico", sizes=[(s, s) for s in sizes])
            Image.open(ROOT / "app" / "assets" / "tray.png").convert("RGBA").save(
                ROOT / "app" / "assets" / "tray.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 48, 64)])
            print("app.ico / app.png OK")
        except ImportError:
            print("Pillow липсва – app.ico не е генерирана")
    except Exception as exc:  # noqa
        import traceback
        traceback.print_exc()
        print("PNG/ICO пропуснати:", exc)

    # звук: кратко „тик" (20 ms, 1.4 kHz, затихващо)
    rate = 22050
    frames = bytearray()
    n = int(rate * 0.02)
    for i in range(n):
        v = math.sin(2 * math.pi * 1400 * i / rate) * (1 - i / n) ** 2 * 0.35
        frames += struct.pack("<h", int(v * 32767))
    with wave.open(str(SOUNDS / "tick.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    print("tick.wav OK")


if __name__ == "__main__":
    main()
