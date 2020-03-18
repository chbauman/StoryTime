import os

import wx
from unittest import TestCase

from lib.main import StoryTimeApp
from tests.test_util import SAMPLE_IMG_DIR

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


class TestMain(TestCase):
    def test_main(self):
        app = wx.App()
        ex = StoryTimeApp(None)

        def fun():
            ex.input_text_field.SetValue("Sample Text")
            ex.OnSave(None)
            ex.OnPhoto(None)
            if not ex.photoTool.IsToggled():
                ex.OnCloseButtonClick(None)
                assert False
            ex.input_text_field.SetValue("Image Sample Text")
            ex.fileDrop.loadedFile = TEST_IMG
            ex.cdDialog.dt = wx.DateTime(2, 11, 2020, 5, 31)
            ex.OnSave(None)
            ex.OnPhoto(None)
            ex.OnCloseButtonClick(None)

        wx.CallAfter(fun)
        app.MainLoop()
        app.Destroy()
