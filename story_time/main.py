#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The main script with the StoryTimeApp.

Run this file to run the app.

TODO:
    - PDF generation! (Without Latex!)
    - Fix webcam glitches (HOW??????).
    - Make header color changeable: https://stackoverflow.com/questions/51000320/wxpython-change-the-headers-color
    - Host documentation somewhere. (Write it first! (Including automatic screenshot generation!??))
    - Indicate diary entries in calendar. (Probably need a custom calendar...)
    - Smoother UI changes (e.g. image loading)
    - Preview: Resolve issue with multiple entries on same Date and time.
    - Center toolbar?
    - Handle image deletion while app is running
    - Remove prints for non-debug scenario
    - Add screenshots to readme.md
    - Adjust dialog fonts (sizes?).
    - Calendar: Add 'now' option that sets the time to now (or set default selected time to now)
"""
from typing import Callable

import wx

from story_time.user_interface import StoryTimeAppUI


def main(_after_fun: Callable = None) -> None:
    """Run the app."""
    app = wx.App()
    ex = StoryTimeAppUI(None)
    ex.Show()
    if _after_fun is not None:
        wx.CallAfter(_after_fun, ex)
    app.MainLoop()


if __name__ == "__main__":
    main()
