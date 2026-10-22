import atexit
import os
import shutil
import tempfile

# Tests check the English texts, independent of the language of the system.
os.environ["STORY_TIME_LANG"] = "en"

# Tests must never read or change the settings of the user.
_config_dir = tempfile.mkdtemp(prefix="story_time_test_config_")
os.environ["STORY_TIME_CONFIG_DIR"] = _config_dir
atexit.register(shutil.rmtree, _config_dir, ignore_errors=True)
