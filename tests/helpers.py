"""Helpers for the tests, without any dependency on the GUI."""

import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from story_time import settings

DATA_DIR = os.path.join(Path(__file__).parent, "test_data")
SAMPLE_IMG_DIR = os.path.join(DATA_DIR, "sample_imgs")
img_dir = os.path.join(DATA_DIR, "Img")
xml_dir = os.path.join(DATA_DIR, "XML")
db_file = os.path.join(DATA_DIR, "story_time.sqlite")


@contextmanager
def create_test_dirs():
    """Creates and removes the folders and the database for testing."""
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    try:
        yield
    finally:
        shutil.rmtree(img_dir, ignore_errors=True)
        shutil.rmtree(xml_dir, ignore_errors=True)
        for leftover in (db_file, db_file + ".importing"):
            if os.path.exists(leftover):
                os.remove(leftover)


@contextmanager
def use_data_dir(dir_to_set):
    """Sets the data folder in the settings and restores them afterwards."""
    old_settings = settings.load_settings()
    settings.set_data_dir(dir_to_set)
    try:
        yield
    finally:
        settings.save_settings(old_settings)


class LazyStore:
    """The test folder's SQLite store, opened on first use.

    Creating it at import time would create the database before the tests
    start from a clean folder.
    """

    def __getattr__(self, name):
        from story_time.sqlite_storage import SqliteEntryStore

        return getattr(SqliteEntryStore(db_file), name)
