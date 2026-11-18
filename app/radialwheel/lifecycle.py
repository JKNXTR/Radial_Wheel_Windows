"""Стартиране/спиране на основното приложение и на лекия слушател на клавиша (когато колелото е затворено)."""
import logging
import subprocess
import sys
import time
from pathlib import Path

from . import winapi

log = logging.getLogger(__name__)
STOP_EVENT = "Local\\RadialWheelListenerStop"
CREATE_NO_WINDOW, DETACHED_PROCESS, NEW_GROUP = 0x08000000, 0x00000008, 0x00000200


def base_command() -> list:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    return [str(pyw if pyw.exists() else exe), str(Path(__file__).resolve().parent.parent / "main.py")]


def _spawn(extra):
    flags = (CREATE_NO_WINDOW | DETACHED_PROCESS | NEW_GROUP) if winapi.IS_WIN else 0
    subprocess.Popen(base_command() + extra, creationflags=flags, close_fds=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def spawn_main(show: bool = True):
    _spawn(["--show"] if show else [])


def spawn_listener():
    _spawn(["--listener"])


def stop_listener() -> bool:
    """Казва на работещия слушател да спре (освобождава клавиша). True, ако е имало такъв."""
    if not winapi.IS_WIN:
        return False
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenEventW.restype = ctypes.c_void_p
    k32.OpenEventW.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p)
    k32.SetEvent.argtypes = (ctypes.c_void_p,)
    k32.CloseHandle.argtypes = (ctypes.c_void_p,)
    h = k32.OpenEventW(0x0002, False, STOP_EVENT)      # EVENT_MODIFY_STATE
    if not h:
        return False
    k32.SetEvent(h)
    k32.CloseHandle(h)
    time.sleep(0.35)                                   # изчакваме UnregisterHotKey
    return True
