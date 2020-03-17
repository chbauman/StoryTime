import wx
from unittest import TestCase

from lib.main import StoryTimeApp


class TestMain(TestCase):
    def test_main(self):
        app = wx.App()
        ex = StoryTimeApp(None)

        def fun():
            ex.OnPhoto(None)
            ex.OnPhoto(None)
            ex.OnCloseButtonClick(None)

        wx.CallAfter(fun)
        app.MainLoop()
