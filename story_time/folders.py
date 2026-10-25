"""The folder of the diary and the folder for temporary files.

There is no state in this module: the folders are objects that are passed to
whoever needs them. This module does not depend on the GUI, the user is asked for
a folder by a function that is passed in.
"""

import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass

from story_time import settings


@dataclass(frozen=True)
class DataFolder:
    """The folder with the data of the diary: the entries and the images."""

    path: str

    @property
    def img_folder(self) -> str:
        """The folder where the images are stored."""
        return os.path.join(self.path, "Img")

    @property
    def db_file(self) -> str:
        """The database with the entries."""
        return os.path.join(self.path, "story_time.sqlite")

    @property
    def xml_folder(self) -> str:
        """The folder with the XML files, where older versions stored the entries."""
        return os.path.join(self.path, "XML")

    def create(self) -> None:
        """Creates the folder and the one for the images if they are missing."""
        os.makedirs(self.img_folder, exist_ok=True)


def get_data_folder(ask_folder: Callable[[], str | None]) -> DataFolder | None:
    """Gets the folder with the diary data from the settings.

    Asks for a folder if there is none yet and creates the sub-folders if they
    do not exist.

    Args:
        ask_folder: Called to ask the user for a folder, returns `None` or an
            empty string if the user does not choose one.

    Returns:
        The data folder, `None` if the user did not choose one.
    """
    path = settings.get_data_dir()
    if path is None:
        path = ask_folder()
        if not path:
            return None
    folder = DataFolder(path)
    folder.create()
    return folder


def save_data_folder(folder: DataFolder) -> None:
    """Stores the data folder in the settings."""
    settings.set_data_dir(folder.path)


class TempFolder:
    """A folder for temporary files, e.g. taken photos.

    It is created when it is first needed and only this folder is removed again.
    """

    def __init__(self) -> None:
        self._path: str | None = None

    @property
    def path(self) -> str:
        """The path of the folder, which is created if it does not exist."""
        if self._path is None or not os.path.isdir(self._path):
            self._path = tempfile.mkdtemp(prefix="story_time_")
        return self._path

    def remove(self) -> None:
        """Removes the folder with its content, if it was created."""
        if self._path is not None and os.path.isdir(self._path):
            shutil.rmtree(self._path)
        self._path = None
