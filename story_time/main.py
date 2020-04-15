#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The main script with the StoryTimeApp.

Run this file to run the app.

TODO:
    - PDF generation!
    - Fix webcam glitches.
    - Indicate diary entries in calendar.
    - Smoother UI changes (e.g. image loading)
    - Host documentation somewhere.
    - Adjust dialog fonts (sizes?).
    - Preview: Resolve issue with multiple entries on same Date and time.
    - Center toolbar?
    - Make header color changeable: https://stackoverflow.com/questions/51000320/wxpython-change-the-headers-color
    - Handle image deletion while app is running
    - Remove prints for non-debug scenario
    - En-/ Disable Next/Previous button if no other entry present
    - Handle non-square images in large view
    - Change black image border to better color
    - Add screenshots to readme.md
"""
from typing import Callable

import wx

from story_time.user_interface import StoryTimeAppUITest


def main(_after_fun: Callable = None):
    """DO ALL THE STUFF.
    """
    app = wx.App()
    ex = StoryTimeAppUITest(None)
    ex.Show()
    if _after_fun is not None:
        wx.CallAfter(_after_fun, ex)
    app.MainLoop()


if __name__ == "__main__":
    main()
