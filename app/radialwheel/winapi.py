"""Тънък слой над Win32 API (ctypes). На не-Windows системи всички функции са безвредни no-op."""
import logging
import sys

log = logging.getLogger(__name__)
IS_WIN = sys.platform == "win32"

# ------------------------------------------------------------------ виртуални клавиши
VK = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "return": 0x0D, "shift": 0xA0, "ctrl": 0xA2, "control": 0xA2,
    "alt": 0xA4, "altgr": 0xA5, "esc": 0x1B, "escape": 0x1B, "space": 0x20, "pageup": 0x21, "pagedown": 0x22,
    "end": 0x23, "home": 0x24, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "insert": 0x2D,
    "delete": 0x2E, "win": 0x5B, "apps": 0x5D, "menu": 0x5D, "voldown": 0xAE, "volup": 0xAF, "mute": 0xAD,
    "plus": 0xBB, "minus": 0xBD, "comma": 0xBC, "period": 0xBE, "`": 0xC0,
}
for _i in range(26):
    VK[chr(ord("a") + _i)] = ord("A") + _i
for _i in range(10):
    VK[str(_i)] = ord("0") + _i
for _i in range(1, 13):
    VK[f"f{_i}"] = 0x6F + _i
EXTENDED = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x5B, 0x5C, 0x5D, 0xA3, 0xA5}

if IS_WIN:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ULONG_PTR = ctypes.c_size_t
    LRESULT = ctypes.c_ssize_t
    WPARAM = ctypes.c_size_t
    LPARAM = ctypes.c_ssize_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.BringWindowToTop.argtypes = (wintypes.HWND,)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    user32.IsWindow.argtypes = (wintypes.HWND,)
    user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
    user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.CallNextHookEx.argtypes = (ctypes.c_void_p, ctypes.c_int, WPARAM, LPARAM)
    user32.CallNextHookEx.restype = LRESULT
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)

    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)
    user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD)
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def parse_combo(combo: str):
    keys = []
    for part in combo.replace(" ", "").split("+"):
        if not part:
            continue
        vk = VK.get(part.lower())
        if vk is None and len(part) == 1:
            vk = ord(part.upper())
        if vk is None:
            raise ValueError(f"Непознат клавиш: {part!r} в комбинацията {combo!r}")
        keys.append(vk)
    return keys


def send_keys(vks):
    """Натиска всички клавиши по ред и ги освобождава в обратен ред (с един SendInput)."""
    if not IS_WIN:
        log.info("send_keys (no-op извън Windows): %s", vks)
        return
    events = []
    for vk in vks:
        events.append((vk, False))
    for vk in reversed(vks):
        events.append((vk, True))
    arr = (INPUT * len(events))()
    for i, (vk, up) in enumerate(events):
        flags = (KEYEVENTF_EXTENDEDKEY if vk in EXTENDED else 0) | (KEYEVENTF_KEYUP if up else 0)
        arr[i].type = 1  # INPUT_KEYBOARD
        arr[i].ki = KEYBDINPUT(vk, 0, flags, 0, 0)
    sent = user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise ctypes.WinError(ctypes.get_last_error())


def send_combo(combo: str):
    send_keys(parse_combo(combo))


# ------------------------------------------------------------------ фокус
def get_foreground() -> int:
    return int(user32.GetForegroundWindow() or 0) if IS_WIN else 0


def force_foreground(hwnd: int):
    """SetForegroundWindow, който работи и когато Windows ограничава смяната на фокуса."""
    if not IS_WIN or not hwnd:
        return
    try:
        fg = user32.GetForegroundWindow()
        cur = kernel32.GetCurrentThreadId()
        fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(fg_tid and fg_tid != cur and user32.AttachThreadInput(cur, fg_tid, True))
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if attached:
            user32.AttachThreadInput(cur, fg_tid, False)
    except Exception:
        log.exception("force_foreground неуспешно")


def foreground_pid() -> int:
    """PID на процеса, чийто прозорец е на преден план (0 при грешка / извън Windows)."""
    if not IS_WIN:
        return 0
    try:
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def restore_foreground(hwnd: int):
    if IS_WIN and hwnd and user32.IsWindow(hwnd):
        try:
            user32.SetForegroundWindow(hwnd)
        except Exception:
            log.exception("restore_foreground неуспешно")


# ------------------------------------------------------------------ системни действия
def lock_workstation():
    if IS_WIN:
        user32.LockWorkStation()


def sleep_system():
    if IS_WIN:
        ctypes.WinDLL("powrprof").SetSuspendState(0, 0, 0)   # 0 = Sleep (не Hibernate)


# ------------------------------------------------------------------ глобален клавиш
HOTKEY_ID = 0xB001
MOD = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
MOD_NOREPEAT = 0x4000


def register_hotkey(mods: int, vk: int) -> bool:
    if not IS_WIN:
        return False
    user32.UnregisterHotKey(None, HOTKEY_ID)
    return bool(user32.RegisterHotKey(None, HOTKEY_ID, mods | MOD_NOREPEAT, vk))


def unregister_hotkey():
    if IS_WIN:
        user32.UnregisterHotKey(None, HOTKEY_ID)


# ------------------------------------------------------------------ глобален бутон на мишката
WH_MOUSE_LL = 14
WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0207, 0x0208
WM_XBUTTONDOWN, WM_XBUTTONUP = 0x020B, 0x020C


class MouseTrigger:
    """Low-level mouse hook. Инсталира се в главната (Qt) нишка, затова callback-ът е безопасен."""

    def __init__(self, callback):
        self._cb = callback
        self._button = "none"
        self._hook = None
        self._proc = None
        self._swallow_up = False

    def set_button(self, button: str):
        self._button = button
        if not IS_WIN:
            return
        if button == "none":
            self.stop()
        elif self._hook is None:
            self._start()

    def _match(self, msg, data):
        xb = (data >> 16) & 0xFFFF
        b = self._button
        if b == "middle":
            return msg in (WM_MBUTTONDOWN, WM_MBUTTONUP)
        if b == "xbutton1":
            return msg in (WM_XBUTTONDOWN, WM_XBUTTONUP) and xb == 1
        if b == "xbutton2":
            return msg in (WM_XBUTTONDOWN, WM_XBUTTONUP) and xb == 2
        return False

    def _start(self):
        def proc(nCode, wParam, lParam):
            try:
                if nCode == 0 and self._button != "none":
                    info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    if self._match(wParam, info.mouseData):
                        if wParam in (WM_MBUTTONDOWN, WM_XBUTTONDOWN):
                            self._cb()
                        return 1  # поглъщаме и натискането, и отпускането
            except Exception:
                log.exception("Грешка в mouse hook")
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._proc = HOOKPROC(proc)
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        if not self._hook:
            log.error("SetWindowsHookEx неуспешно: %s", ctypes.WinError(ctypes.get_last_error()))
            self._proc = None

    def stop(self):
        if IS_WIN and self._hook:
            user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        self._proc = None
