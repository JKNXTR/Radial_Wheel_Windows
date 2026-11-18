"""Глобален клавиш (RegisterHotKey) и/или бутон на мишката за извикване на колелото."""
import ctypes
import logging

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from . import winapi

log = logging.getLogger(__name__)
WM_HOTKEY = 0x0312


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey):
        super().__init__()
        self._on = on_hotkey

    def nativeEventFilter(self, event_type, message):
        try:
            if winapi.IS_WIN and bytes(event_type) == b"windows_generic_MSG":
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == winapi.HOTKEY_ID:
                    self._on()
                    return True, 0
        except Exception:
            log.exception("nativeEventFilter грешка")
        return False, 0


class Triggers(QObject):
    activated = Signal()

    def __init__(self, app):
        super().__init__()
        self._filter = _Filter(self.activated.emit)
        app.installNativeEventFilter(self._filter)
        self._mouse = winapi.MouseTrigger(self.activated.emit)

    def reload(self, cfg) -> tuple[bool, str]:
        """Прилага настройките. Връща (успех, съобщение_за_грешка)."""
        msg = ""
        ok = True
        hk = cfg["hotkey"]
        winapi.unregister_hotkey()
        if hk["enabled"] and winapi.IS_WIN:
            mods = sum(v for k, v in winapi.MOD.items() if hk.get(k))
            vk = winapi.VK.get(hk["key"].lower())
            if vk is None and len(hk["key"]) == 1:
                vk = ord(hk["key"].upper())
            if not vk or not mods:
                ok, msg = False, "Невалидна комбинация (нужен е поне един модификатор и клавиш)."
            elif not winapi.register_hotkey(mods, vk):
                err = ctypes.WinError(ctypes.get_last_error())
                ok, msg = False, f"Комбинацията е заета от друга програма ({err})."
                log.error("RegisterHotKey неуспешно: %s", err)
        self._mouse.set_button(cfg["mouse_trigger"])
        return ok, msg

    def shutdown(self):
        winapi.unregister_hotkey()
        self._mouse.stop()
