#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The main script with the StoryTimeApp.

Run this file to run the app.

TODO:
    - PDF generation!
    - Fix webcam glitches.
    - Make header color changeable: https://stackoverflow.com/questions/51000320/wxpython-change-the-headers-color
    - Host documentation somewhere.
    - Indicate diary entries in calendar.
    - Smoother UI changes (e.g. image loading)
    - Preview: Resolve issue with multiple entries on same Date and time.
    - Center toolbar?
    - Handle image deletion while app is running
    - Remove prints for non-debug scenario
    - En-/ Disable Next/Previous button if no other entry present
    - Change black image border to better color
    - Handle non-square images in large view
    - Add screenshots to readme.md
    - Improve button position and size (fit longest text)
    - Adjust dialog fonts (sizes?).
    - Calendar: Add 'now' option that sets the time to now
    - Photo mode toggle: No changing of current date! (Implement above point first)
"""
from typing import Callable

import wx

from story_time.user_interface import StoryTimeAppUITest


def main(_after_fun: Callable = None):
    """Run the app.
    """
    app = wx.App()
    ex = StoryTimeAppUITest(None)
    ex.Show()
    if _after_fun is not None:
        wx.CallAfter(_after_fun, ex)
    app.MainLoop()


if __name__ == "__main__":
    main()
