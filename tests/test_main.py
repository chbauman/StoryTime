import os

import wx
from unittest import TestCase

from lib.main import StoryTimeApp, ID_MENU_PHOTO
from tests.test_util import SAMPLE_IMG_DIR, DATA_DIR, change_info_txt, create_test_dirs

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


class TestMain(TestCase):
    def test_main(self):

        app = wx.App()
        ex = StoryTimeApp(None)

        def take_selfie(s_dlg):
            def inner():
                s_dlg.accept_diag.OnTakePic(None)

            s_dlg.OnTakePic(None, inner)

        def clickOK(dlg):
            dlg.OnClose(None)

        def fun():
            # Set text, change date and save
            ex.input_text_field.SetValue("Sample Text")
            ex.OnChangeDate(None, clickOK)
            ex.OnSave(None)

            # Change to photo mode, add image and save
            ex.OnPhoto(None)
            ex.toolbar.ToggleTool(ID_MENU_PHOTO, True)
            ex.input_text_field.SetValue("Image Sample Text")
            ex.fileDrop.loadedFile = TEST_IMG
            ex.cdDialog.dt = wx.DateTime(2, 11, 2020, 5, 31)
            ex.OnSave(None)

            # Take a selfie
            ex.OnSelfie(None, take_selfie)
            ex.input_text_field.SetValue("Selfie Test Text")
            ex.OnSave(None)

            # Change back to text input and close
            ex.OnPhoto(None)
            ex.toolbar.ToggleTool(ID_MENU_PHOTO, False)
            ex.OnCloseButtonClick(None)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                wx.CallAfter(fun)
                app.MainLoop()
                app.Destroy()
