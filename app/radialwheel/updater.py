"""Актуализация от .zip архив: проверка, разархивиране, подмяна на папката app/ и рестарт."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from . import __version__, winapi
from .paths import data_dir, resource_root


class UpdateError(Exception):
    pass


def parse_version(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4]) or (0,)


def inspect_zip(path: str):
    """Връща (префикс на app/ в архива, версия). Хвърля UpdateError, ако архивът не е валиден."""
    if not zipfile.is_zipfile(path):
        raise UpdateError("not_zip")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for n in names:
            if n.replace("\\", "/").endswith("app/radialwheel/__init__.py"):
                prefix = n.replace("\\", "/")[: -len("radialwheel/__init__.py")]   # напр. "RadialWheel/app/"
                if prefix.count("/") <= 2:
                    break
        else:
            raise UpdateError("bad_zip")
        if prefix + "main.py" not in names:
            raise UpdateError("bad_zip")
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)', z.read(prefix + "radialwheel/__init__.py").decode("utf-8", "ignore"))
        return prefix, (m.group(1) if m else "?")


def stage(path: str, prefix: str) -> Path:
    """Разархивира само app/ в нова временна папка (с защита срещу ../ пътища)."""
    dest = Path(tempfile.mkdtemp(prefix="rw_update_"))
    root = dest.resolve()
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            n = info.filename.replace("\\", "/")
            if not n.startswith(prefix) or info.is_dir():
                continue
            target = (dest / n[len(prefix):]).resolve()
            if root not in target.parents:
                raise UpdateError("bad_zip")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    return dest


def can_update() -> bool:
    return not getattr(sys, "frozen", False) and (resource_root() / "main.py").exists()


HELPER = r'''
import ctypes, os, shutil, subprocess, sys, time, traceback
pid, new, app, log = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
cmd = sys.argv[5:]
def say(m):
    with open(log, "a", encoding="utf-8") as f: f.write(time.strftime("%H:%M:%S ") + m + "\n")
def alive(p):
    if os.name == "nt":
        h = ctypes.windll.kernel32.OpenProcess(0x100000, False, p)
        if not h: return False
        r = ctypes.windll.kernel32.WaitForSingleObject(h, 0); ctypes.windll.kernel32.CloseHandle(h)
        return r == 0x102
    try: os.kill(p, 0); return True
    except OSError: return False
for _ in range(100):
    if not alive(pid): break
    time.sleep(0.2)
time.sleep(0.5)
bak = app + ".bak"
try:
    if os.path.exists(bak): shutil.rmtree(bak)
    shutil.copytree(app, bak, ignore=shutil.ignore_patterns("__pycache__"))
    for root, dirs, files in os.walk(new):
        rel = os.path.relpath(root, new)
        os.makedirs(os.path.join(app, rel), exist_ok=True)
        for f in files:
            for attempt in range(10):
                try: shutil.copy2(os.path.join(root, f), os.path.join(app, rel, f)); break
                except PermissionError: time.sleep(0.5)
            else: raise PermissionError(f)
    say("Обновяването е успешно")
except Exception:
    say("ГРЕШКА, връщам старата версия\n" + traceback.format_exc())
    try:
        shutil.rmtree(app, ignore_errors=True); shutil.copytree(bak, app)
    except Exception: say(traceback.format_exc())
shutil.rmtree(new, ignore_errors=True)
flags = 0x08000000 | 0x00000008 | 0x00000200 if os.name == "nt" else 0
subprocess.Popen(cmd, creationflags=flags, close_fds=True)
'''


def launch_helper(staged: Path):
    """Стартира независим помощник, който след затваряне на приложението подменя файловете и го пуска отново."""
    helper = data_dir() / "apply_update.py"
    helper.write_text(HELPER, encoding="utf-8")
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    py = str(pyw if winapi.IS_WIN and pyw.exists() else exe)
    from .lifecycle import base_command
    flags = (0x08000000 | 0x00000008 | 0x00000200) if winapi.IS_WIN else 0
    subprocess.Popen([py, str(helper), str(os.getpid()), str(staged), str(resource_root()),
                      str(data_dir() / "update.log")] + base_command() + ["--show"],
                     creationflags=flags, close_fds=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
