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
    - Host documentation somewhere.
    - Adjust colors.
    - Achieve 100% test coverage.
    - Preview: Resolve issue with multiple entries on same Date and time.
    - Center toolbar?
    - Better fonts (size and family!)
    - Color buttons!
    - Make header color changeable: https://stackoverflow.com/questions/51000320/wxpython-change-the-headers-color
    - Handle image deletion while app is running
    - Handle app resizing! (Similar as for the photo enlargement)
    - Remove prints for non-debug scenario
    - En-/ Disable Next/Previous button if no other entry present
    - Handle non-square images in large view
    - Change black image border to better color
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
