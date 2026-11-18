"""Стартиране/спиране на основното приложение и на лекия слушател на клавиша (когато колелото е затворено)."""
import logging
import os
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


def _our_markers() -> list:
    """Низове, по които разпознаваме процесите на този инструмент (команден ред / изпълним файл)."""
    if getattr(sys, "frozen", False):
        return [os.path.normcase(sys.executable)]
    return [os.path.normcase(str(Path(__file__).resolve().parent.parent / "main.py"))]


def kill_stale(min_age: float = 8.0, wait: float = 1.5) -> int:
    """Затваря стари/увиснали процеси на инструмента (основни и слушатели), без текущия процес, родителите и децата му.
    Процеси по-млади от `min_age` секунди не се пипат (може да са нормален паралелен старт). Връща брой затворени."""
    try:
        import psutil
    except Exception:
        log.warning("psutil липсва – проверката за стари екземпляри е пропусната")
        return 0
    me = psutil.Process()
    protected = {me.pid} | {p.pid for p in me.parents()} | {p.pid for p in me.children(recursive=True)}
    markers = _our_markers()
    victims = []
    for p in psutil.process_iter(["pid", "cmdline", "create_time"]):
        try:
            if p.info["pid"] in protected:
                continue
            cmd = [os.path.normcase(a) for a in (p.info["cmdline"] or [])]
            if not any(m in a for m in markers for a in cmd):
                continue
            if time.time() - (p.info["create_time"] or 0) < min_age:
                continue
            victims.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    for p in victims:
        try:
            log.warning("Затварям стар екземпляр pid=%s: %s", p.pid, " ".join(p.cmdline())[:200])
            p.terminate()
        except Exception:
            log.exception("terminate неуспешно за %s", p.pid)
    gone, alive = psutil.wait_procs(victims, timeout=wait)
    for p in alive:
        try:
            p.kill()
        except Exception:
            log.exception("kill неуспешно за %s", p.pid)
    return len(victims)
