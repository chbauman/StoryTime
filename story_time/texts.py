"""Access to the texts shown in the user interface.

All texts live in JSON catalogs in `story_time/locales`, one file per
language (e.g. `en.json`). Use `tr` to get a text by its key:

    tr("main.date_line", date="Monday, 1.1.2024")

To add a language, copy `en.json` to `<language code>.json` and translate the
values, keeping the keys and the `{placeholders}`. Texts missing in a catalog
fall back to English.

The language is taken from the environment variable `STORY_TIME_LANG`,
otherwise from the system locale, otherwise English is used.
"""

import json
import locale
import os
import sys
from functools import cache
from pathlib import Path

DEFAULT_LANGUAGE = "en"
LOCALE_DIR = Path(__file__).resolve().parent / "locales"
LANGUAGE_ENV_VAR = "STORY_TIME_LANG"

_language: str | None = None


def available_languages() -> list[str]:
    """Returns the codes of all languages that have a catalog."""
    return sorted(f.stem for f in LOCALE_DIR.glob("*.json"))


@cache
def load_catalog(language: str) -> dict[str, str]:
    """Loads the catalog of the given language, empty if there is none."""
    path = LOCALE_DIR / f"{language}.json"
    if not path.is_file():
        return {}
    with open(path, encoding="utf8") as f:
        return json.load(f)


def _system_language() -> str | None:
    """Finds the language code (e.g. `de`) of the system, if possible."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value and value not in ("C", "POSIX"):
            return value
    if sys.platform == "win32":
        import ctypes

        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return locale.windows_locale.get(lang_id)
    return locale.getlocale()[0]


def detect_language() -> str:
    """Chooses the language to use, among the available ones."""
    candidates = [os.environ.get(LANGUAGE_ENV_VAR), _system_language()]
    for cand in candidates:
        if not cand:
            continue
        code = cand.replace("-", "_").split("_")[0].split(".")[0].lower()
        if code in available_languages():
            return code
    return DEFAULT_LANGUAGE


def set_language(language: str | None = None) -> None:
    """Sets the language, `None` means to detect it again."""
    global _language
    _language = language


def get_language() -> str:
    global _language
    if _language is None:
        _language = detect_language()
    return _language


def tr(key: str, **kwargs: object) -> str:
    """Returns the text with the given key in the current language.

    The placeholders of the text are replaced with the keyword arguments.
    Falls back to English and finally to the key itself.
    """
    text = load_catalog(get_language()).get(key)
    if text is None:
        text = load_catalog(DEFAULT_LANGUAGE).get(key, key)
    return text.format(**kwargs) if kwargs else text
