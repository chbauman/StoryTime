import os

import wx
from unittest import TestCase

from lib import util
from lib.main import StoryTimeApp, ID_MENU_PHOTO
from tests.test_util import (
    SAMPLE_IMG_DIR,
    DATA_DIR,
    change_info_txt,
    create_test_dirs,
    replace_dir_ask,
)

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


class TestMain(TestCase):
    def test_main(self):

        app = wx.App()
        ex = StoryTimeApp(None)

        def take_selfie(s_dlg):
            def inner():
                s_dlg.accept_diag.OnTakePic(None)

            s_dlg.OnTakePic(None, inner)

        def click_on_close(dlg):
            dlg.OnClose(None)

        def discard_text(d):
            d.OnOK(None)

        def fun():
            # Set text, change date and save
            ex.OnSave(None, _no_text_fun=click_on_close)
            ex.input_text_field.SetValue("Sample Text")
            ex.OnChangeDate(None, click_on_close)
            ex.OnSave(None)

            # Change to photo mode, add image and save
            ex.OnPhoto(None)
            ex.toolbar.ToggleTool(ID_MENU_PHOTO, True)
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSave(None, _no_text_fun=click_on_close)
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

            # Set text and try changing to photo mode
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(None, _photo_fun=click_on_close)
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(None, take_selfie, _photo_fun=discard_text)
            ex.toolbar.ToggleTool(ID_MENU_PHOTO, True)

            def new_ask_fun():
                return None

            def other_ask_fun():
                return util.data_path

            with replace_dir_ask(new_ask_fun):
                ex.OnChangeDir(None)
            with replace_dir_ask(other_ask_fun):
                ex.OnChangeDir(None)

            # Exit
            ex.OnCloseButtonClick(None)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                wx.CallAfter(fun)
                app.MainLoop()
                app.Destroy()
