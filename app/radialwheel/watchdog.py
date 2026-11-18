"""Откриване на „замръзване“ на интерфейса: ако GUI нишката не отговаря >2,5 s, пълният stack на всички нишки
се записва в radialwheel.log (faulthandler). Така се вижда точно къде е блокирало."""
import faulthandler
import logging
import os
import threading
import time

from PySide6.QtCore import QTimer

from .paths import LOG_FILE

log = logging.getLogger(__name__)
STALL_S = 2.5
KILL_S = 10.0            # при толкова секунди замръзване процесът се прекратява и надзорникът го рестартира
_beat = [time.monotonic()]
_fh = None


def start(parent):
    """Стартира heartbeat в GUI нишката и наблюдател във фонова нишка."""
    global _fh
    try:
        _fh = open(LOG_FILE(), "a", encoding="utf-8")
    except Exception:
        log.exception("Watchdog: логът не може да се отвори")
        return
    try:
        faulthandler.enable(file=_fh, all_threads=True)      # при срив на ниво C/COM записва stack в лога
    except Exception:
        log.exception("faulthandler.enable неуспешно")
    timer = QTimer(parent)
    timer.setInterval(250)
    timer.timeout.connect(lambda: _beat.__setitem__(0, time.monotonic()))
    timer.start()

    def watch():
        reported = False
        while True:
            time.sleep(0.5)
            lag = time.monotonic() - _beat[0]
            if lag > KILL_S and os.environ.get("RADIALWHEEL_SUPERVISED"):
                try:
                    _fh.write(f"=== {time.strftime('%H:%M:%S')} Интерфейсът не отговаря {lag:.0f} s – принудително затваряне, надзорникът ще рестартира ===\n")
                    _fh.flush()
                except Exception:
                    pass
                os._exit(3)
            if lag > STALL_S and not reported:
                reported = True
                try:
                    _fh.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} Интерфейсът не отговаря от {lag:.1f} s – stack на всички нишки ===\n")
                    _fh.flush()
                    faulthandler.dump_traceback(file=_fh, all_threads=True)
                    _fh.flush()
                except Exception:
                    pass
            elif lag <= STALL_S and reported:
                reported = False
                try:
                    _fh.write(f"=== {time.strftime('%H:%M:%S')} Интерфейсът отново отговаря ===\n")
                    _fh.flush()
                except Exception:
                    pass
    threading.Thread(target=watch, daemon=True, name="ui-watchdog").start()
    parent._watchdog_timer = timer
