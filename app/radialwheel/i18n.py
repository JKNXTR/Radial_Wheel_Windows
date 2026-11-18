"""Локализация: всички текстове са в lang/lang_bg.json и lang/lang_en.json."""
import json
import logging

from .paths import LANG

log = logging.getLogger(__name__)
_strings = {}
_fallback = {}
LANGUAGES = {"en": "English", "bg": "Български", "de": "Deutsch", "fr": "Français", "es": "Español", "it": "Italiano",
             "pt": "Português", "nl": "Nederlands", "pl": "Polski", "cs": "Čeština", "ro": "Română", "el": "Ελληνικά",
             "tr": "Türkçe", "ru": "Русский", "uk": "Українська", "sv": "Svenska", "hu": "Magyar", "ja": "日本語",
             "zh": "简体中文", "ko": "한국어"}


def _load(code):
    try:
        return json.loads((LANG / f"lang_{code}.json").read_text(encoding="utf-8"))
    except Exception:
        log.exception("Неуспешно зареждане на езиков файл %s", code)
        return {}


def set_language(code: str):
    global _strings, _fallback
    _fallback = _load("en")
    _strings = _load(code) if code in LANGUAGES and code != "en" else _fallback


def tr(key: str, *args) -> str:
    s = _strings.get(key) or _fallback.get(key) or key
    if args:
        try:
            return s.format(*args)
        except Exception:
            return s
    return s
