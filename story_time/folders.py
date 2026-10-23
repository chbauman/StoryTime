"""The folders of the diary and the folder for temporary files.

This module keeps the data folder of the running app. It does not depend on
the GUI, the user is asked for a folder by a function that is passed in.
"""

import os
import shutil
import tempfile
from typing import Callable, Optional

from story_time import settings

# The state of the running app, set with `update_folder`. Initialized values
# should never be used.
data_path = ""  #: The folder containing the image and the xml folder.
img_folder = "if/you/see/this/its/a/bug"  #: The folder where the images are stored.
xml_folder = (
    "if/you/see/this/its/a/bug"  #: The folder where the xml documents are stored.
)

_temp_folder: Optional[str] = None


def update_folder(new_data_path: str) -> None:
    """Update global path variables if data folder is changed."""
    global data_path
    global img_folder
    global xml_folder

    data_path = new_data_path
    img_folder = os.path.join(new_data_path, "Img")
    xml_folder = os.path.join(new_data_path, "XML")


def create_dir(dir_name: str) -> None:
    """Creates the given directory recursively."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


def create_xml_and_img_folder(base_folder: str) -> None:
    """Create a folder for the XML and the image files in `base_folder`."""
    os.makedirs(os.path.join(base_folder, "XML"), exist_ok=True)
    os.makedirs(os.path.join(base_folder, "Img"), exist_ok=True)


def get_data_folder(ask_folder: Callable[[], Optional[str]]) -> Optional[str]:
    """Gets the folder with the diary data from the settings.

    Asks for a folder if there is none yet and creates the sub-folders if they
    do not exist.

    Args:
        ask_folder: Called to ask the user for a folder, returns `None` or an
            empty string if the user does not choose one.

    Returns:
        The path of the data folder, `None` if the user did not choose one.
    """
    fol_path = settings.get_data_dir()
    if fol_path is None:
        fol_path = ask_folder()
        if not fol_path:
            return None
    create_xml_and_img_folder(fol_path)
    return fol_path


def save_data_folder() -> None:
    """Stores the current data folder in the settings."""
    settings.set_data_dir(data_path)


def get_temp_folder() -> str:
    """Returns the folder for temporary files, e.g. taken photos.

    It is created on first use and is removed by `remove_temp_folder`.
    """
    global _temp_folder
    if _temp_folder is None or not os.path.isdir(_temp_folder):
        _temp_folder = tempfile.mkdtemp(prefix="story_time_")
    return _temp_folder


def remove_temp_folder() -> None:
    """Removes the folder returned by `get_temp_folder`, but nothing else."""
    global _temp_folder
    if _temp_folder is not None and os.path.isdir(_temp_folder):
        shutil.rmtree(_temp_folder)
    _temp_folder = None
