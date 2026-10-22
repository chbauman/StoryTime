"""Per-user settings of the app.

The settings are stored as JSON in the config folder of the user, not in
the installed package, where they could not be written and would be lost
when the package is updated. The folder can be changed with the environment
variable `STORY_TIME_CONFIG_DIR`, which is useful for tests.
"""

import json
import os
import sys
import tempfile
from typing import Any, Optional

CONFIG_DIR_ENV_VAR = "STORY_TIME_CONFIG_DIR"
SETTINGS_FILE_NAME = "settings.json"
APP_DIR_NAME = "StoryTime"

#: File where older versions stored the data folder, inside the package.
LEGACY_INFO_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Info.txt")


def config_dir() -> str:
    """Returns the folder for the settings of the user."""
    override = os.environ.get(CONFIG_DIR_ENV_VAR)
    if override:
        return override
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, APP_DIR_NAME)


def settings_file() -> str:
    """Returns the path of the settings file."""
    return os.path.join(config_dir(), SETTINGS_FILE_NAME)


def load_settings() -> dict[str, Any]:
    """Loads the settings, they are empty if there is no valid settings file."""
    try:
        with open(settings_file(), encoding="utf8") as f:
            settings = json.load(f)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}


def save_settings(settings: dict[str, Any]) -> None:
    """Saves the settings. Writes to a temporary file first, so the old file is
    never left half written."""
    os.makedirs(config_dir(), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=config_dir(), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf8") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, settings_file())
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _read_legacy_data_dir() -> Optional[str]:
    """Reads the data folder from the file of older versions, if it is valid."""
    try:
        with open(LEGACY_INFO_FILE, encoding="utf8") as f:
            lines = f.readlines()
    except OSError:
        return None
    path = lines[0].strip() if lines else ""
    return path if path and os.path.isdir(path) else None


def get_data_dir() -> Optional[str]:
    """Returns the folder with the diary data, `None` if none is set (yet).

    The folder of older versions is taken over once if there are no settings.
    """
    data_dir = load_settings().get("data_dir")
    if isinstance(data_dir, str) and os.path.isdir(data_dir):
        return data_dir
    if data_dir is None:
        data_dir = _read_legacy_data_dir()
        if data_dir is not None:
            set_data_dir(data_dir)
            return data_dir
    return None


def set_data_dir(path: str) -> None:
    """Stores the folder with the diary data."""
    settings = load_settings()
    settings["data_dir"] = path
    save_settings(settings)
