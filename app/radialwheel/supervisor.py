"""Надзорник: при срив, грешка, принудително затваряне или замръзване инструментът се рестартира сам.

Процесът, стартиран от потребителя/автостарта, е лек надзорник (без Qt). Той пуска същинското приложение
като дъщерен процес (`--child`). Ако то завърши с код != 0 (срив, access violation, убит процес, самозатворил
се замръзнал интерфейс), след RESTART_DELAY секунди се стартира отново; новият процес затваря всички
предишни версии (lifecycle.kill_stale). Нормален изход (Изход от трея, код 0) спира и надзорника.
"""
import logging
import os
import subprocess
import sys
import time

log = logging.getLogger("supervisor")
RESTART_DELAY = 5.0          # секунди до рестарта
FAST_WINDOW = 120.0          # ако се срине няколко пъти в този прозорец -> по-дълга пауза
FAST_LIMIT = 5
SLOW_DELAY = 60.0


def _child_cmd(args, first):
    here = os.path.abspath(sys.argv[0])
    cmd = [sys.executable] + ([] if getattr(sys, "frozen", False) else [here]) + ["--child"]
    if args.autostart or not first:
        cmd.append("--autostart")        # след рестарт не се показва колелото
    elif args.show:
        cmd.append("--show")
    return cmd


def run(args) -> int:
    flags = 0x08000000 if sys.platform == "win32" else 0         # CREATE_NO_WINDOW
    env = dict(os.environ, RADIALWHEEL_SUPERVISED="1")
    crashes = []
    first = True
    log.info("Надзорникът стартира (pid %s)", os.getpid())
    while True:
        started = time.monotonic()
        try:
            proc = subprocess.Popen(_child_cmd(args, first), env=env, creationflags=flags,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            code = proc.wait()
        except Exception:
            log.exception("Стартирането на приложението неуспешно")
            code = -1
        first = False
        if code == 0:
            log.info("Приложението завърши нормално – надзорникът излиза.")
            return 0
        now = time.monotonic()
        crashes = [t for t in crashes if now - t < FAST_WINDOW] + [now]
        delay = SLOW_DELAY if len(crashes) > FAST_LIMIT else RESTART_DELAY
        log.warning("Приложението завърши неочаквано (код %s, работило %.0f s) – рестарт след %.0f s",
                    code, now - started, delay)
        time.sleep(delay)
