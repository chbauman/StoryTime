import importlib.util
import re
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "changelog_notes", ROOT / "tools" / "changelog_notes.py"
)
assert SPEC is not None and SPEC.loader is not None
changelog_notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(changelog_notes)

SAMPLE = """# Changelog

## [Unreleased]

### Added
- Something new.

## [1.2.0] - 2026-01-02

### Fixed
- A bug.

## [1.1.0] - 2025-12-01

- Older.
"""


class TestNotesFor(TestCase):
    def test_section_of_a_version(self):
        notes = changelog_notes.notes_for(SAMPLE, "1.2.0")
        assert notes == "### Fixed\n- A bug.\n"

    def test_last_section_and_the_unreleased_one(self):
        assert changelog_notes.notes_for(SAMPLE, "1.1.0") == "- Older.\n"
        assert "Something new" in changelog_notes.notes_for(SAMPLE, "Unreleased")

    def test_the_version_is_not_a_prefix_of_another(self):
        with self.assertRaises(ValueError):
            changelog_notes.notes_for(SAMPLE, "1.2")

    def test_unknown_and_empty_sections_fail(self):
        with self.assertRaises(ValueError):
            changelog_notes.notes_for(SAMPLE, "9.9.9")
        with self.assertRaises(ValueError):
            changelog_notes.notes_for(
                "## [1.0.0] - 2026-01-01\n\n## [0.9.0]\n- x\n", "1.0.0"
            )


class TestChangelog(TestCase):
    def setUp(self):
        self.text = (ROOT / "CHANGELOG.md").read_text(encoding="utf8")

    def test_there_is_a_section_for_what_is_not_released(self):
        assert changelog_notes.notes_for(self.text, "Unreleased").strip()

    def test_released_versions_have_a_date(self):
        headings = re.findall(r"^## \[(.+?)\](.*)$", self.text, re.MULTILINE)
        for name, rest in headings:
            if name != "Unreleased":
                assert re.fullmatch(r" - \d{4}-\d{2}-\d{2}", rest), name
                assert changelog_notes.notes_for(self.text, name)

    def test_version_file_is_a_version(self):
        version = (ROOT / "version.txt").read_text(encoding="utf8").strip()
        assert re.fullmatch(r"\d+\.\d+\.\d+", version)
