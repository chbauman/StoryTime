#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The main script with the StoryTimeApp.

Run this file to run the app.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com

TODO:
- Preview including image entries.
- Add more type hints.
- Add more documentation, esp. for function arguments.
- PDF generation?
"""

import wx

from lib.main import StoryTimeApp


def main():
    """DO ALL THE STUFF.
    """
    app = wx.App()
    ex = StoryTimeApp(None)
    ex.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
