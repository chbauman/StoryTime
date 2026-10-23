import subprocess
import sys
from pathlib import Path
from unittest import TestCase

ROOT = str(Path(__file__).resolve().parent.parent)

#: The modules with the logic of the app, which must work without the GUI.
PURE_MODULES = [
    "story_time.controller",
    "story_time.dates",
    "story_time.entries",
    "story_time.folders",
    "story_time.images",
    "story_time.settings",
    "story_time.shortcuts",
    "story_time.sqlite_storage",
    "story_time.storage",
    "story_time.texts",
    "story_time.xml_storage",
]


class TestPureModules(TestCase):
    def test_no_gui_is_imported(self):
        """The logic does not import wx or OpenCV, so it can be tested without a GUI."""
        for module in PURE_MODULES:
            code = (
                f"import sys\nsys.path.insert(0, {ROOT!r})\nimport {module}\n"
                "loaded = sorted(m for m in ('wx', 'cv2') if m in sys.modules)\n"
                "print(','.join(loaded))"
            )
            result = subprocess.run(
                [sys.executable, "-I", "-c", code],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result.stdout.strip() == "", f"{module} imports {result.stdout}"
