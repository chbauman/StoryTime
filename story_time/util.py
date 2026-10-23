#!/usr/bin/env python3
"""Helpers that use wx: colors, fonts, images, dropping files and the
conversion of dates from and to `wx.DateTime`.
"""

import os
from datetime import datetime
from typing import Any, Callable

import wx

from story_time import dates
from story_time.images import is_supported_image


def resource_filename(rel_path: str) -> str:
    """Returns the absolute path of a file shipped inside the package."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), rel_path)


icon_path = resource_filename("Icons")

# Set colors
teal = wx.Colour(15, 118, 110)  #: Accent color.
light_teal = wx.Colour(209, 242, 236)
very_light_teal = wx.Colour(247, 252, 251)
dark_text = wx.Colour(19, 78, 74)
white = wx.Colour(255, 255, 255)

header_col = light_teal  #: Background of the toolbar and the info lines.
but_bg_col = teal  #: Background of the bars with buttons and the date line.
text_bg_col = very_light_teal  #: Background of the text fields.
header_text_col = dark_text  #: Text color on `header_col`.
bar_text_col = white  #: Text color on `but_bg_col`.

# Fonts
header_f_info = wx.FontInfo(12).Family(wx.FONTFAMILY_SWISS).Bold()
button_f_info = wx.FontInfo(12).Family(wx.FONTFAMILY_SWISS).Bold()
dialog_f_info = wx.FontInfo(17).Family(wx.FONTFAMILY_SWISS).Bold()


def scale_bitmap(bitmap: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
    """Rescales a bitmap to a given size.

    Converting it to image, rescaling and converting it back.
    """
    image = bitmap.ConvertToImage()
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.Bitmap(image)
    return result


def wx_datetime_to_datetime(date: wx.DateTime) -> datetime:
    """Converts a wx.DateTime to a python datetime."""
    return datetime(
        date.GetYear(),
        date.GetMonth() + 1,
        date.GetDay(),
        date.GetHour(),
        date.GetMinute(),
        date.GetSecond(),
    )


def format_date_time(date_time: datetime) -> str:
    """Formats the given datetime for display, with the name of the weekday."""
    weekday = wx.DateTime.GetWeekDayName(
        datetime_to_wx_datetime(date_time).GetWeekDay()
    )
    return dates.format_date_time(date_time, weekday)


def datetime_to_wx_datetime(date: datetime) -> wx.DateTime:
    """Converts a python datetime to a wx.DateTime."""
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    return wx.DateTime(day, month - 1, year, hour, date.minute, date.second)


class FileDrop(wx.FileDropTarget):
    """Drop Target to drop images to be added."""

    def __init__(self, window: Any, on_image: Callable[[str], bool]) -> None:
        """
        Args:
            window: The window the files can be dropped on.
            on_image: Called with the path of a dropped image, returns whether it
                was accepted.
        """
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.on_image = on_image

    def OnDropFiles(self, x: Any, y: Any, filenames: list) -> bool:
        """Handle the dropped files, only the first one is used.

        Checks if the extension is supported.
        """
        if len(filenames) > 1:
            print("Can only process one file at a time.")
        curr_file = filenames[0]
        if not is_supported_image(curr_file):
            _, ext = os.path.splitext(curr_file)
            print(f"ERROR: Unsupported file type: {ext[1:].lower()}")
            return False
        return self.on_image(curr_file)


def getImageToShow(
    filename: str, height: int = 180, border: int = 5, width: int = None
) -> wx.Bitmap:
    """Converts the specified image to a bitmap of according size.

    Preserves the aspect ratio by padding with a color.

    Args:
        filename: The path to the file.
        height: The size of the returned image.
        border: Border width.
        width: The width of the returned image, same as height if not specified.

    Returns:
        The bitmap with the specified size
    """
    bor_2 = 2 * border
    border_col = teal

    # Load from file and convert to image
    wxBmp = wx.Bitmap(filename)
    image = wxBmp.ConvertToImage()

    # Handle sizes
    if width is None:
        width = height

    # Reserve space for border
    height -= bor_2
    width -= bor_2

    imgSize = image.GetSize()
    img_w, img_h = imgSize
    too_high = img_h / img_w > height / width
    fac = height / img_h if too_high else width / img_w

    # Rescale image
    image.Rescale(
        int(round(fac * img_w)), int(round(fac * img_h)), wx.IMAGE_QUALITY_HIGH
    )
    new_img_w, new_img_h = image.GetSize()

    # Pad image
    border_w = border + (width - new_img_w) // 2
    border_h = border + (height - new_img_h) // 2
    img_sz = wx.Size(width + bor_2, height + bor_2)
    image.Resize(
        img_sz,
        wx.Point(border_w, border_h),
        border_col[0],
        border_col[1],
        border_col[2],
    )

    # Convert to bitmap and return
    result = wx.Bitmap(image)
    return result
