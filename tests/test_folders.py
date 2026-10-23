import os
import shutil
import tempfile
from unittest import TestCase

from story_time import folders, settings


class TestFolders(TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="story_time_test_folders_")
        self.addCleanup(shutil.rmtree, self.base, True)
        self.old_state = (folders.data_path, folders.img_folder, folders.xml_folder)
        self.old_settings = settings.load_settings()

    def tearDown(self):
        folders.data_path, folders.img_folder, folders.xml_folder = self.old_state
        settings.save_settings(self.old_settings)

    def test_update_folder(self):
        folders.update_folder(self.base)
        assert folders.data_path == self.base
        assert folders.img_folder == os.path.join(self.base, "Img")
        assert folders.xml_folder == os.path.join(self.base, "XML")

    def test_dir_creation(self):
        folders.create_xml_and_img_folder(self.base)
        folders.create_xml_and_img_folder(self.base)  # Is fine if they exist
        assert os.path.isdir(os.path.join(self.base, "Img"))
        assert os.path.isdir(os.path.join(self.base, "XML"))

    def test_create_dir(self):
        nested = os.path.join(self.base, "a", "b", "c")
        folders.create_dir(nested)
        folders.create_dir(nested)
        assert os.path.isdir(nested)

    def test_data_folder_from_settings(self):
        settings.set_data_dir(self.base)

        def ask():
            raise AssertionError("must not ask")

        assert folders.get_data_folder(ask) == self.base
        assert os.path.isdir(os.path.join(self.base, "XML"))

    def test_data_folder_is_asked_for(self):
        settings.save_settings({})
        asked = []

        def ask():
            asked.append(True)
            return self.base

        assert folders.get_data_folder(ask) == self.base
        assert asked == [True]
        assert os.path.isdir(os.path.join(self.base, "Img"))

    def test_no_folder_chosen(self):
        settings.save_settings({})
        assert folders.get_data_folder(lambda: None) is None
        assert folders.get_data_folder(lambda: "") is None
        # Nothing is created in the current folder
        assert not os.path.exists("XML") and not os.path.exists("Img")

    def test_save_data_folder(self):
        folders.update_folder(self.base)
        folders.save_data_folder()
        assert settings.get_data_dir() == self.base


class TestTempFolder(TestCase):
    def tearDown(self):
        folders.remove_temp_folder()

    def test_own_folder_in_system_temp(self):
        folder = folders.get_temp_folder()
        assert os.path.isdir(folder)
        assert os.path.dirname(folder) == os.path.realpath(tempfile.gettempdir()) or (
            os.path.dirname(folder) == tempfile.gettempdir()
        )
        assert folders.get_temp_folder() == folder

    def test_remove_only_removes_own_folder(self):
        other = tempfile.mkdtemp(prefix="story_time_test_other_")
        try:
            with open(os.path.join(other, "keep.txt"), "w") as f:
                f.write("keep")
            folder = folders.get_temp_folder()
            with open(os.path.join(folder, "photo.png"), "w") as f:
                f.write("x")
            folders.remove_temp_folder()
            assert not os.path.exists(folder)
            assert os.path.exists(os.path.join(other, "keep.txt"))

            # Removing twice is fine and a new folder is created when needed
            folders.remove_temp_folder()
            assert os.path.isdir(folders.get_temp_folder())
        finally:
            shutil.rmtree(other, ignore_errors=True)
