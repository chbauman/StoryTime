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


@contextmanager
def create_test_dirs():
    """Creates and removes temporary folders for testing."""
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    try:
        yield
    finally:
        shutil.rmtree(img_dir, ignore_errors=True)
        shutil.rmtree(xml_dir, ignore_errors=True)


@contextmanager
def use_data_dir(dir_to_set):
    """Sets the data folder in the settings and restores them afterwards."""
    old_settings = settings.load_settings()
    settings.set_data_dir(dir_to_set)
    try:
        yield
    finally:
        settings.save_settings(old_settings)
