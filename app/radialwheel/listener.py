"""Лек фонов слушател (само ctypes, без Qt): държи глобалния клавиш, докато колелото е затворено.
При натискане стартира колелото (--show) и излиза. Стартира се с:  main.py --listener"""
import json
import logging
import subprocess

from . import lifecycle, winapi
from .paths import CONFIG_FILE

log = logging.getLogger(__name__)


def hotkey_from_config(data: dict):
    """(модификатори, vk) от config.json или None, ако клавишът е изключен/невалиден."""
    hk = data.get("hotkey", {})
    if not hk.get("enabled", True):
        return None
    mods = sum(v for k, v in winapi.MOD.items() if hk.get(k))
    key = str(hk.get("key", "Space"))
    vk = winapi.VK.get(key.lower()) or (ord(key.upper()) if len(key) == 1 else None)
    return (mods, vk) if mods and vk else None


def run() -> int:
    if not winapi.IS_WIN:
        return 1
    import ctypes
    from ctypes import wintypes
    k32, u32 = winapi.kernel32, winapi.user32
    for fn in (k32.CreateMutexW, k32.CreateEventW):
        fn.restype = ctypes.c_void_p
    k32.CreateMutexW(None, False, "Local\\RadialWheelListener")
    if ctypes.get_last_error() == 183:                 # ERROR_ALREADY_EXISTS – вече има слушател
        return 0
    stop = k32.CreateEventW(None, True, False, lifecycle.STOP_EVENT)
    try:
        data = json.loads(CONFIG_FILE().read_text(encoding="utf-8"))
    except Exception:
        log.exception("Слушателят не може да прочете config.json – ползвам Ctrl+Alt+Space")
        data = {}
    hk = hotkey_from_config(data) if data else (winapi.MOD["ctrl"] | winapi.MOD["alt"], winapi.VK["space"])
    if hk is None or not winapi.register_hotkey(*hk):
        log.error("Слушателят не успя да регистрира клавиша (%s)", hk)
        return 1
    u32.MsgWaitForMultipleObjects.argtypes = (wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), wintypes.BOOL,
                                              wintypes.DWORD, wintypes.DWORD)
    u32.MsgWaitForMultipleObjects.restype = wintypes.DWORD
    handles = (ctypes.c_void_p * 1)(stop)
    msg = wintypes.MSG()
    log.info("Слушателят е активен")
    while True:
        r = u32.MsgWaitForMultipleObjects(1, handles, False, 0xFFFFFFFF, 0x04FF)   # QS_ALLINPUT
        if r == 0:                                     # основното приложение поиска клавиша
            break
        while u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            if msg.message == 0x0312 and msg.wParam == winapi.HOTKEY_ID:
                winapi.unregister_hotkey()
                lifecycle.spawn_main(show=True)
                return 0
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))
    winapi.unregister_hotkey()
    return 0
