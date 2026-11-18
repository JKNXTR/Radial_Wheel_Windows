"""Пътища до ресурси и до потребителските данни."""
import os
import sys
from pathlib import Path

from . import APP_NAME


def resource_root() -> Path:
    """Папката с assets/ и lang/ (работи и при PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


ASSETS = resource_root() / "assets"
ICONS = ASSETS / "icons"
SOUNDS = ASSETS / "sounds"
LANG = resource_root() / "lang"


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_FILE = lambda: data_dir() / "config.json"  # noqa: E731
LOG_FILE = lambda: data_dir() / "radialwheel.log"  # noqa: E731
