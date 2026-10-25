import json
import string
from unittest import TestCase

from story_time import texts
from story_time.texts import DEFAULT_LANGUAGE, LOCALE_DIR, available_languages, tr


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class TestTexts(TestCase):
    def setUp(self):
        texts.set_language("en")

    def tearDown(self):
        texts.set_language(None)

    def test_catalogs_are_consistent(self):
        """All catalogs have the keys and placeholders of the English one."""
        default = texts.load_catalog(DEFAULT_LANGUAGE)
        assert default
        for lang in available_languages():
            catalog = texts.load_catalog(lang)
            assert set(catalog) == set(default), lang
            for key, text in catalog.items():
                assert placeholders(text) == placeholders(default[key]), (lang, key)

    def test_catalogs_are_valid_json(self):
        for path in LOCALE_DIR.glob("*.json"):
            with open(path, encoding="utf8") as f:
                assert isinstance(json.load(f), dict)

    def test_placeholders_are_replaced(self):
        assert tr("main.date_line", date="today") == "Date: today"

    def test_other_language(self):
        texts.set_language("de")
        assert tr("toolbar.new.name") == "Neuer Eintrag"

    def test_fallbacks(self):
        assert tr("no.such.key") == "no.such.key"
        # Unknown languages fall back to English
        texts.set_language("xx")
        assert tr("toolbar.new.name") == "New entry"

    def test_language_detection(self):
        import os

        old = {v: os.environ.get(v) for v in ("STORY_TIME_LANG", "LC_ALL", "LANG")}
        try:
            os.environ["STORY_TIME_LANG"] = "de_CH.UTF-8"
            assert texts.detect_language() == "de"
            os.environ["STORY_TIME_LANG"] = "xx"
            os.environ["LC_ALL"] = "C"
            os.environ["LANG"] = "C"
            assert texts.detect_language() in available_languages()
        finally:
            for var, val in old.items():
                if val is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = val
