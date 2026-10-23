import os
import shutil
import tempfile
from unittest import TestCase

from story_time import settings
from story_time.folders import (
    DataFolder,
    TempFolder,
    get_data_folder,
    save_data_folder,
)


class TestDataFolder(TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="story_time_test_folders_")
        self.addCleanup(shutil.rmtree, self.base, True)
        old_settings = settings.load_settings()
        self.addCleanup(settings.save_settings, old_settings)

    def test_sub_folders(self):
        folder = DataFolder(self.base)
        assert folder.path == self.base
        assert folder.img_folder == os.path.join(self.base, "Img")
        assert folder.xml_folder == os.path.join(self.base, "XML")
        assert folder.db_file == os.path.join(self.base, "story_time.sqlite")

    def test_folders_are_independent(self):
        # There is no global state, each folder knows its paths
        other = DataFolder(os.path.join(self.base, "other"))
        assert DataFolder(self.base).xml_folder != other.xml_folder

    def test_creation(self):
        folder = DataFolder(os.path.join(self.base, "new", "diary"))
        folder.create()
        folder.create()  # Is fine if they exist
        assert os.path.isdir(folder.img_folder)
        # The folder of the XML files is only there for diaries of older versions
        assert not os.path.exists(folder.xml_folder)

    def test_data_folder_from_settings(self):
        settings.set_data_dir(self.base)

        def ask():
            raise AssertionError("must not ask")

        assert get_data_folder(ask) == DataFolder(self.base)
        assert os.path.isdir(os.path.join(self.base, "Img"))

    def test_data_folder_is_asked_for(self):
        settings.save_settings({})
        asked = []

        def ask():
            asked.append(True)
            return self.base

        assert get_data_folder(ask) == DataFolder(self.base)
        assert asked == [True]
        assert os.path.isdir(os.path.join(self.base, "Img"))

    def test_no_folder_chosen(self):
        settings.save_settings({})
        assert get_data_folder(lambda: None) is None
        assert get_data_folder(lambda: "") is None
        # Nothing is created in the current folder
        assert not os.path.exists("Img") and not os.path.exists("story_time.sqlite")

    def test_save_data_folder(self):
        save_data_folder(DataFolder(self.base))
        assert settings.get_data_dir() == self.base


class TestTempFolder(TestCase):
    def test_own_folder_in_system_temp(self):
        temp = TempFolder()
        self.addCleanup(temp.remove)
        folder = temp.path
        assert os.path.isdir(folder)
        assert os.path.dirname(folder) == os.path.realpath(tempfile.gettempdir()) or (
            os.path.dirname(folder) == tempfile.gettempdir()
        )
        assert temp.path == folder

    def test_not_created_until_needed(self):
        temp = TempFolder()
        temp.remove()  # Nothing to remove, is fine

    def test_each_one_has_its_own_folder(self):
        first, second = TempFolder(), TempFolder()
        self.addCleanup(first.remove)
        self.addCleanup(second.remove)
        assert first.path != second.path

    def test_remove_only_removes_own_folder(self):
        other = tempfile.mkdtemp(prefix="story_time_test_other_")
        temp = TempFolder()
        try:
            with open(os.path.join(other, "keep.txt"), "w") as f:
                f.write("keep")
            folder = temp.path
            with open(os.path.join(folder, "photo.png"), "w") as f:
                f.write("x")
            temp.remove()
            assert not os.path.exists(folder)
            assert os.path.exists(os.path.join(other, "keep.txt"))

            # Removing twice is fine and a new folder is created when needed
            temp.remove()
            assert os.path.isdir(temp.path)
        finally:
            temp.remove()
            shutil.rmtree(other, ignore_errors=True)
