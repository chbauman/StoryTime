"""Date and time helpers, without any dependency on the GUI.

All functions work with `datetime`.
"""

import os
import re
from datetime import datetime
from typing import Optional

from story_time.texts import tr


def pad_int_str(int_to_pad: int, n: int = 2) -> str:
    """Converts an integer to a string, padding with leading zeros
    to get n characters. Intended for date and time formatting.
    """
    base = str(int_to_pad)
    for k in range(n - 1):
        if int_to_pad < 10 ** (k + 1):
            base = "0" + base
    return base


def check_date_time(
    y: int, mon: int, d: int, h: int = 0, minute: int = 0, sec: int = 0
) -> bool:
    """Checks if the provided date and time is valid."""
    try:
        datetime(y, mon, d, h, minute, sec)
    except ValueError:
        return False
    return True


def format_date_time(date_time: datetime, weekday: str) -> str:
    """Formats the given datetime for display.

    Args:
        date_time: The datetime to format.
        weekday: The name of the weekday of `date_time`, which depends on the
            language and is therefore given.
    """
    return tr(
        "main.datetime",
        weekday=weekday,
        day=date_time.day,
        month=date_time.month,
        year=date_time.year,
        hour=pad_int_str(date_time.hour),
        minute=pad_int_str(date_time.minute),
        second=pad_int_str(date_time.second),
    )


def img_name_from_time(date_time: datetime) -> str:
    """Gives the image basename (without extension) from the datetime."""
    return (
        f"IMG_{pad_int_str(date_time.year, 4)}{pad_int_str(date_time.month)}"
        f"{pad_int_str(date_time.day)}_{pad_int_str(date_time.hour)}"
        f"{pad_int_str(date_time.minute)}{pad_int_str(date_time.second)}"
    )


def date_from_image_name(img_file: str) -> Optional[datetime]:
    """Extracts the date information from the image name.

    Tries to extract the date and optionally the time.
    If extracted date is not valid or there is no date
    contained in the name, returns None.
    """
    _, filename = os.path.split(img_file)
    # Extract all numbers from string
    nums = re.findall(r"\d+", filename)
    if len(nums) < 1:
        return None
    date = int(nums[0])
    # Year must be greater than 1
    if date < 10000:
        return None
    year = date // 10000
    rem = date - year * 10000
    month = rem // 100
    day = rem - month * 100
    hour = mins = sec = 0

    # Extract time
    if len(nums) > 1:
        num_curr = int(nums[1])
        len_num = len(nums[1])
        if len_num == 6:
            sec = num_curr % 100
            num_curr = num_curr // 100
        if len_num == 4 or len_num == 6:
            mins = num_curr % 100
            hour = num_curr // 100

    if not check_date_time(year, month, day, hour, mins, sec):
        return None
    return datetime(year, month, day, hour, mins, sec)


def file_modified_time(path: str) -> datetime:
    """Reads the time a file was last modified, without fractions of seconds."""
    return datetime.fromtimestamp(os.path.getmtime(path)).replace(microsecond=0)


def date_of_image_file(img_file: str) -> datetime:
    """Tries to extract the date from a filename.

    If there is none, returns the modified time of the file.
    """
    name_date = date_from_image_name(img_file)
    return file_modified_time(img_file) if name_date is None else name_date
