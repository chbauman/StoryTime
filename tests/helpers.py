"""Helpers for the tests, without any dependency on the GUI."""

import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from story_time import folders, settings

DATA_DIR = os.path.join(Path(__file__).parent, "test_data")
SAMPLE_IMG_DIR = os.path.join(DATA_DIR, "sample_imgs")
img_dir = os.path.join(DATA_DIR, "Img")
xml_dir = os.path.join(DATA_DIR, "XML")


@contextmanager
def create_test_dirs():
    """Creates and removes temporary folders for testing."""
    folders.create_dir(img_dir)
    folders.create_dir(xml_dir)
    try:
        yield
    finally:
        shutil.rmtree(img_dir, ignore_errors=True)
        shutil.rmtree(xml_dir, ignore_errors=True)


@contextmanager
def use_data_dir(dir_to_set):
    """Uses the given data folder, also in the settings, and restores all after."""
    old_settings = settings.load_settings()
    old_folders = (folders.data_path, folders.img_folder, folders.xml_folder)
    folders.update_folder(dir_to_set)
    folders.save_data_folder()
    try:
        yield
    finally:
        settings.save_settings(old_settings)
        folders.data_path, folders.img_folder, folders.xml_folder = old_folders
