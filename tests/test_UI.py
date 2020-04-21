import os
from unittest import TestCase

import wx

from story_time import util
from story_time.main import main
from story_time.user_interface import StoryTimeAppUI
from tests.test_util import (
    SAMPLE_IMG_DIR,
    DATA_DIR,
    change_info_txt,
    create_test_dirs,
    replace_dir_ask,
)

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


class TestMain2(TestCase):
    @staticmethod
    def discard_text(d):
        d.OnOK(None)

    @staticmethod
    def click_on_close(d):
        d.OnClose(None)

    @staticmethod
    def resize_and_close(d):
        d.Size = wx.Size(400, 400)
        d.OnSize(None)
        d.OnIdle(None)
        d.Close()

    @staticmethod
    def take_selfie(s_dlg):
        def inner():
            s_dlg.accept_diag.OnTakePic(None)

        s_dlg.OnTakePic(None, inner)

    def play_with_app_exit(self, ex, app):
        def fun():
            # Set text and try to exit
            ex.input_text_field.SetValue("Sample Text")
            ex.OnX(None, self.click_on_close)
            ex.OnX(None, self.discard_text)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                wx.CallAfter(fun)
                app.MainLoop()
                app.Destroy()

    def play_with_app_preview(self, ex, app):
        def fun():
            # Add text entry
            ex.input_text_field.SetValue("Sample Text")
            ex.OnSave(None)

            # Take a selfie
            ex.OnSelfie(None, self.take_selfie)
            ex.input_text_field.SetValue("Selfie Test Text")
            ex.OnSave(None)

            # Check preview
            ex.next_entry(None)
            ex.prev_entry(None)
            ex.prev_entry(None)

            ex.OnX(None, self.discard_text)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                wx.CallAfter(fun)
                app.MainLoop()
                app.Destroy()

    def play_with_app(self, ex, app):
        def fun():
            # Set text, change date and save
            ex.OnSave(None, _no_text_fun=self.click_on_close)
            ex.input_text_field.SetValue("Sample Text")
            ex.OnChangeDate(None, self.click_on_close)
            ex.OnSave(None)

            # Toggle preview
            ex.toggle_prev_img(None)

            # Change to photo mode, add image and save
            ex.OnPhoto(None)
            ex.toolbar.ToggleTool(ex.photoTool.Id, True)
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSave(None, _no_text_fun=self.click_on_close)
            ex.fileDrop.loadedFile = TEST_IMG
            ex.cdDialog.dt = wx.DateTime(2, 11, 2020, 5, 31)
            ex.OnSave(None)

            # Take a selfie
            ex.on_taken_image_clicked(None)
            ex.OnSelfie(None, self.take_selfie)
            ex.input_text_field.SetValue("Selfie Test Text")
            ex.on_taken_image_clicked(None, self.resize_and_close)
            ex.OnSave(None)

            ex.prev_img_name = TEST_IMG
            ex.on_prev_image_clicked(None, self.resize_and_close)
            ex.prev_img_name = None

            # Change back to text input and close
            ex.OnPhoto(None)
            ex.toolbar.ToggleTool(ex.photoTool.Id, False)

            # Set text and try changing to photo mode
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(None, _photo_fun=self.click_on_close)
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(None, self.take_selfie, _photo_fun=self.discard_text)
            ex.toolbar.ToggleTool(ex.photoTool.Id, True)

            def new_ask_fun():
                return None

            def other_ask_fun():
                return util.data_path

            with replace_dir_ask(new_ask_fun):
                ex.OnChangeDir(None)
            with replace_dir_ask(other_ask_fun):
                ex.OnChangeDir(None)

            # Exit
            ex.OnCloseButtonClick(None, self.click_on_close)
            ex.OnCloseButtonClick(None, self.discard_text)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                wx.CallAfter(fun)
                app.MainLoop()
                app.Destroy()
        pass

    def test_main_func(self):
        def close(d):
            d.OnX(None)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                main(close)

    def test_main_UI(self):
        app = wx.App()
        ex = StoryTimeAppUI(None)
        self.play_with_app(ex, app)

    def test_UI_exit(self):
        app = wx.App()
        ex = StoryTimeAppUI(None)
        self.play_with_app_exit(ex, app)

    def test_UI_preview(self):
        app = wx.App()
        ex = StoryTimeAppUI(None)
        self.play_with_app_preview(ex, app)
