"""Входна точка: python main.py [--autostart] [--show]"""
import argparse
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Позволява стартиране и като `python main.py`, и като frozen exe
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from radialwheel.paths import LOG_FILE  # noqa: E402


def setup_logging():
    handlers = [RotatingFileHandler(LOG_FILE(), maxBytes=512_000, backupCount=2, encoding="utf-8")]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def hook(exc_type, exc, tb):
        logging.getLogger("uncaught").error("Необработено изключение:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = hook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--autostart", action="store_true", help="стартиране с Windows (тихо)")
    parser.add_argument("--listener", action="store_true", help="лек слушател на клавиша (колелото е затворено)")
    parser.add_argument("--show", action="store_true", help="покажи колелото веднага")
    args = parser.parse_args()
    setup_logging()
    log = logging.getLogger("main")

    if args.listener:                      # без Qt – стартира се мигновено и струва почти нищо
        from radialwheel.listener import run
        return run()

    from PySide6.QtWidgets import QApplication
    from radialwheel import APP_NAME, __version__
    from radialwheel.app import Controller, notify_running_instance

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    # единствен екземпляр: втори старт само показва колелото в първия
    if notify_running_instance(b"hide" if args.autostart else b"show"):
        log.info("Вече работи друг екземпляр – изход.")
        return 0
    try:
        ctrl = Controller(app, show_now=args.show)
        log.info("Стартирано (v%s, Python %s)", __version__, sys.version.split()[0])
        return app.exec()
    except Exception:
        log.exception("Фатална грешка при стартиране")
        return 1


if __name__ == "__main__":
    sys.exit(main())
