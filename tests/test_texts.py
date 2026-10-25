import ast
import json
import string
from pathlib import Path
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

    def test_all_texts_are_used_and_exist(self):
        """No text is left over and no text used by the code is missing."""
        package = Path(texts.__file__).parent
        literal, suffixes, constants = set(), set(), set()
        for path in package.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    constants.add(node.value)
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "tr"
                    and node.args
                ):
                    continue
                key = node.args[0]
                if isinstance(key, ast.Constant):
                    literal.add(key.value)
                elif isinstance(key, ast.IfExp):
                    # tr("one" if condition else "other")
                    literal.update(
                        branch.value
                        for branch in (key.body, key.orelse)
                        if isinstance(branch, ast.Constant)
                    )
                elif isinstance(key, ast.JoinedStr) and isinstance(
                    key.values[-1], ast.Constant
                ):
                    # tr(f"{prefix}.name"): the prefixes are strings in the code
                    suffixes.add(key.values[-1].value)
                else:
                    self.fail(f"The key is not a text: {ast.unparse(key)}")

        catalog = texts.load_catalog(DEFAULT_LANGUAGE)
        assert not literal - set(catalog), "Texts that are used but missing"
        unused = {
            key
            for key in catalog
            if key not in literal
            and not any(
                key.endswith(suffix) and key[: -len(suffix)] in constants
                for suffix in suffixes
            )
        }
        assert not unused, f"Texts that nothing uses: {sorted(unused)}"

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
