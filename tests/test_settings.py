import os
import shutil
import tempfile
from unittest import TestCase
from unittest.mock import patch

from story_time import settings


class TestSettings(TestCase):
    def setUp(self):
        self.config_dir = tempfile.mkdtemp(prefix="story_time_test_settings_")
        self.data_dir = tempfile.mkdtemp(prefix="story_time_test_data_")
        env = patch.dict(os.environ, {settings.CONFIG_DIR_ENV_VAR: self.config_dir})
        env.start()
        self.addCleanup(env.stop)
        # Never take over the file of a real installation
        legacy = patch.object(
            settings, "LEGACY_INFO_FILE", os.path.join(self.config_dir, "no_info.txt")
        )
        legacy.start()
        self.addCleanup(legacy.stop)
        self.addCleanup(shutil.rmtree, self.config_dir, True)
        self.addCleanup(shutil.rmtree, self.data_dir, True)

    def test_default_config_dir_is_per_user(self):
        with patch.dict(os.environ, {settings.CONFIG_DIR_ENV_VAR: ""}):
            path = settings.config_dir()
        assert path.endswith(settings.APP_DIR_NAME)
        assert os.path.expanduser("~") in path or "XDG_CONFIG_HOME" in os.environ
        # Definitely not inside the installed package
        assert not path.startswith(os.path.dirname(os.path.realpath(settings.__file__)))

    def test_roundtrip(self):
        assert settings.load_settings() == {}
        assert settings.get_data_dir() is None
        settings.set_data_dir(self.data_dir)
        assert settings.get_data_dir() == self.data_dir
        # No temporary files are left behind
        assert os.listdir(settings.config_dir()) == [settings.SETTINGS_FILE_NAME]

    def test_other_settings_are_kept(self):
        settings.save_settings({"other": 1})
        settings.set_data_dir(self.data_dir)
        assert settings.load_settings() == {"other": 1, "data_dir": self.data_dir}

    def test_invalid_file(self):
        os.makedirs(settings.config_dir(), exist_ok=True)
        for content in ["not json {", "[1, 2]"]:
            with open(settings.settings_file(), "w") as f:
                f.write(content)
            assert settings.load_settings() == {}
            assert settings.get_data_dir() is None

    def test_missing_data_dir_is_ignored(self):
        settings.set_data_dir(os.path.join(self.data_dir, "does_not_exist"))
        assert settings.get_data_dir() is None

    def test_failed_save_keeps_old_file(self):
        settings.set_data_dir(self.data_dir)
        failing_dump = patch("story_time.settings.json.dump", side_effect=RuntimeError)
        with failing_dump, self.assertRaises(RuntimeError):
            settings.save_settings({"data_dir": "other"})
        assert settings.get_data_dir() == self.data_dir
        assert os.listdir(settings.config_dir()) == [settings.SETTINGS_FILE_NAME]

    def test_legacy_info_file_is_taken_over_once(self):
        legacy_file = os.path.join(self.config_dir, "Info.txt")
        with open(legacy_file, "w") as f:
            f.write(self.data_dir)
        with patch.object(settings, "LEGACY_INFO_FILE", legacy_file):
            assert settings.get_data_dir() == self.data_dir
            assert settings.load_settings() == {"data_dir": self.data_dir}

            # Afterwards the settings count, even if the old file changes
            other = tempfile.mkdtemp(prefix="story_time_test_other_")
            self.addCleanup(shutil.rmtree, other, True)
            with open(legacy_file, "w") as f:
                f.write(other)
            assert settings.get_data_dir() == self.data_dir

    def test_invalid_legacy_info_file(self):
        legacy_file = os.path.join(self.config_dir, "Info.txt")
        for content in ["NoDirectorySpecified", ""]:
            with open(legacy_file, "w") as f:
                f.write(content)
            with patch.object(settings, "LEGACY_INFO_FILE", legacy_file):
                assert settings.get_data_dir() is None
