from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import wx

from story_time.util import (
    DISABLED_OPACITY,
    FileDrop,
    centered_bitmap,
    datetime_to_wx_datetime,
    disabled_bitmap,
    format_date_time,
    hide_caret,
    scale_bitmap,
    wx_datetime_to_datetime,
)
from tests.wx_helpers import create_app


class TestUtil(TestCase):
    def test_wx_datetime_conversion(self):
        dt = datetime(2020, 12, 2, 5, 31, 7)
        wx_dt = datetime_to_wx_datetime(dt)
        assert (wx_dt.GetDay(), wx_dt.GetMonth(), wx_dt.GetYear()) == (2, 11, 2020)
        assert wx_dt.IsEqualTo(wx.DateTime(2, 11, 2020, 5, 31, 7))
        assert wx_datetime_to_datetime(wx_dt) == dt

    def test_format_dt(self):
        res = format_date_time(datetime(2020, 12, 2, 5, 31))
        assert ",".join(res.split(",")[1:]) == " 2.12.2020, Time: 05:31:00"
        # The weekday comes from wx
        assert res.split(",")[0] == wx.DateTime.GetWeekDayName(wx.DateTime.Wed)

    def test_centered_bitmap(self):
        with create_app():
            image = wx.Image(10, 6)
            image.SetRGB(wx.Rect(0, 0, 10, 6), 255, 0, 0)
            image.InitAlpha()
            result = centered_bitmap(wx.Bitmap(image), 30, 20)
            pixels = result.ConvertToImage()
            opaque = [
                (x, y)
                for x in range(30)
                for y in range(20)
                if pixels.GetAlpha(x, y) == 255
            ]
            assert result.GetSize() == (30, 20)
            # The rectangle is in the middle, the rest is transparent
            assert min(opaque) == (10, 7) and max(opaque) == (19, 12)
            assert len(opaque) == 60 and pixels.GetAlpha(0, 0) == 0
            assert pixels.GetRed(12, 9) == 255

    def test_disabled_bitmap(self):
        with create_app():
            image = wx.Image(4, 4)
            image.SetRGB(wx.Rect(0, 0, 4, 4), 15, 118, 110)
            image.SetAlpha(bytes([200] * 16))
            result = disabled_bitmap(wx.Bitmap(image)).ConvertToImage()
            assert (result.GetWidth(), result.GetHeight()) == (4, 4)
            assert result.GetRed(1, 1) == result.GetGreen(1, 1) == result.GetBlue(1, 1)
            assert result.GetAlpha(1, 1) == int(200 * DISABLED_OPACITY)

    def test_hide_caret_does_nothing_but_on_windows(self):
        window = MagicMock()
        with patch("story_time.util.sys.platform", "linux"):
            hide_caret(window)
        window.GetHandle.assert_not_called()

    def test_scale_bitmap(self):
        with create_app():
            bitmap = wx.Bitmap(40, 20)
            scaled = scale_bitmap(bitmap, 10, 10)
            assert (scaled.GetWidth(), scaled.GetHeight()) == (10, 10)


class TestFileDrop(TestCase):
    def test_file_drop(self):
        dropped = []

        def on_image(path):
            dropped.append(path)
            return True

        drop = FileDrop(None, on_image)
        assert drop.OnDropFiles(0, 0, ["test/IMG_20201202_053100.jpg"])
        # Only the first file is used
        assert drop.OnDropFiles(0, 0, ["test/IMG_20201202_053100.png", "fail"])
        assert dropped == [
            "test/IMG_20201202_053100.jpg",
            "test/IMG_20201202_053100.png",
        ]

    def test_unsupported_files_are_not_passed_on(self):
        dropped = []
        drop = FileDrop(None, lambda path: dropped.append(path) or True)
        assert not drop.OnDropFiles(0, 0, ["fail"])
        assert not drop.OnDropFiles(0, 0, ["notes.txt"])
        assert dropped == []

    def test_result_of_the_function_is_returned(self):
        drop = FileDrop(None, lambda path: False)
        assert not drop.OnDropFiles(0, 0, ["a.jpg"])
