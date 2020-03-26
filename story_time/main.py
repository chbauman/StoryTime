#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The main script with the StoryTimeApp.

Run this file to run the app.

TODO:
    - PDF generation!
    - Fix webcam glitches.
    - Resize images (and text?) when resizing window.
    - Indicate diary entries in calendar.
    - Smoother UI changes (e.g. image loading)
    - Enlarge image when clicked.
    - Host documentation somewhere.

"""

import wx

from story_time.user_interface import StoryTimeAppUITest


def main():
    """DO ALL THE STUFF.
    """
    app = wx.App()
    ex = StoryTimeAppUITest(None)
    ex.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
