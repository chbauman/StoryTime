import os
import tempfile
from datetime import datetime
from unittest import TestCase

from story_time.dates import (
    check_date_time,
    date_from_image_name,
    date_of_image_file,
    file_modified_time,
    format_date_time,
    img_name_from_time,
    pad_int_str,
)


class TestDates(TestCase):
    def test_string_pad(self):
        assert pad_int_str(4, 4) == "0004"
        assert pad_int_str(4) == "04"
        assert pad_int_str(12) == "12"
        assert pad_int_str(1234, 2) == "1234"

    def test_check_date_time(self):
        assert check_date_time(2020, 12, 2, 5, 31, 0)
        assert check_date_time(2020, 2, 29)
        assert not check_date_time(2021, 2, 29)
        assert not check_date_time(2020, 13, 1)
        assert not check_date_time(2020, 1, 1, 24)

    def test_name_from_time(self):
        assert img_name_from_time(datetime(2020, 12, 2, 5, 31)) == "IMG_20201202_053100"
        assert (
            img_name_from_time(datetime(1999, 1, 9, 23, 5, 7)) == "IMG_19990109_230507"
        )

    def test_date_extraction(self):
        expected = datetime(2020, 12, 2, 5, 31)
        assert date_from_image_name("test/IMG_20201202_053100.jpg") == expected
        assert date_from_image_name("IMG_20201202_0531.jpg") == expected
        # The date alone is enough, the time is then midnight
        assert date_from_image_name("photo_20201202.png") == datetime(2020, 12, 2)
        # The name is round trip of the one given to the images
        name = img_name_from_time(expected)
        assert date_from_image_name(name + ".jpg") == expected

    def test_invalid_date_extraction(self):
        assert date_from_image_name("test/IMG_00001202_053100.jpg") is None
        assert date_from_image_name("test/IMG_20003202_053100.jpg") is None
        assert date_from_image_name("test/IMG_20201302_053100.jpg") is None
        assert date_from_image_name("test/IMG_20201202_253100.jpg") is None
        assert date_from_image_name("holiday.jpg") is None
        assert date_from_image_name("img_123.jpg") is None

    def test_date_ignores_numbers_in_the_folder(self):
        assert date_from_image_name("/data/20200101/holiday.jpg") is None

    def test_format_date_time(self):
        res = format_date_time(datetime(2020, 12, 2, 5, 31), "Wednesday")
        assert res == "Wednesday, 2.12.2020, Time: 05:31:00"

    def test_modified_time(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test_file.png")
            before = datetime.now().replace(microsecond=0)
            with open(path, "w") as f:
                f.write("test")
            after = datetime.now()

            modified = file_modified_time(path)
            assert before <= modified <= after
            assert modified.microsecond == 0

            # Without a date in the name the modified time is used
            assert date_of_image_file(path) == modified

            # A date in the name wins
            dated = os.path.join(folder, "IMG_20201202_053100.png")
            os.rename(path, dated)
            assert date_of_image_file(dated) == datetime(2020, 12, 2, 5, 31)
