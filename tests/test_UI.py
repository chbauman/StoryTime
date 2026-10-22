import os
from unittest import TestCase

import wx

from story_time import util
from story_time.main import main
from story_time.user_interface import StoryTimeAppUI, shortcut_for
from tests.test_util import (
    DATA_DIR,
    SAMPLE_IMG_DIR,
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
    def click_on_factory(method_name: str):
        def click_on(d):
            getattr(d, method_name)(None)

        return click_on

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

        wx.CallAfter(fun)
        app.MainLoop()
        app.Destroy()

    def play_with_app_preview(self, ex, app):
        def fun():
            # Add text entry
            ex.input_text_field.SetValue("Sample Text")
            ex.OnSave(None)

            # Take a selfie
            ex.OnSelfie(None, self.take_selfie, _no_cam_fun=self.discard_text)
            ex.input_text_field.SetValue("Selfie Test Text")
            ex.OnSave(None, _no_text_fun=self.discard_text)

            # Check preview
            ex.next_entry(None)
            ex.next_entry(None)
            ex.prev_entry(None)
            ex.prev_entry(None)
            ex.prev_entry(None)

            ex.OnX(None, self.discard_text)

        wx.CallAfter(fun)
        app.MainLoop()
        app.Destroy()

    def play_with_app(self, ex, app):
        def fun():
            # Set text, change date and save
            ex.OnSave(None, _no_text_fun=self.click_on_close)
            ex.input_text_field.SetValue("Sample Text")
            ex.OnChangeDate(None, self.click_on_factory("set_now_and_close"))
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
            ex.OnSelfie(None, self.take_selfie, _no_cam_fun=self.discard_text)
            ex.input_text_field.SetValue("Selfie Test Text")
            ex.on_taken_image_clicked(None, self.resize_and_close)
            ex.OnSave(None, _no_text_fun=self.discard_text)

            ex.prev_img_name = TEST_IMG
            ex.on_prev_image_clicked(None, self.resize_and_close)
            ex.prev_img_name = None

            # Change back to text input and close
            ex.OnPhoto(None, self.discard_text)
            ex.toolbar.ToggleTool(ex.photoTool.Id, False)

            # Set text and try changing to photo mode
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(
                None, _photo_fun=self.click_on_close, _no_cam_fun=self.discard_text
            )
            ex.input_text_field.SetValue("Image Sample Text")
            ex.OnSelfie(
                None,
                self.take_selfie,
                _photo_fun=self.discard_text,
                _no_cam_fun=self.discard_text,
            )
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
            ex.OnX(None, self.click_on_close)
            ex.OnX(None, self.discard_text)

        wx.CallAfter(fun)
        app.MainLoop()
        app.Destroy()
        pass

    @staticmethod
    def run_in_test_dir(play):
        """Creates the app using the test data folder and plays with it."""
        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                app = wx.App()
                ex = StoryTimeAppUI(None)
                play(ex, app)

    def test_main_func(self):
        def close(d):
            d.OnX(None)

        with change_info_txt(DATA_DIR):
            with create_test_dirs():
                main(close)

    def test_main_UI(self):
        self.run_in_test_dir(self.play_with_app)

    def test_UI_exit(self):
        self.run_in_test_dir(self.play_with_app_exit)

    def test_UI_preview(self):
        self.run_in_test_dir(self.play_with_app_preview)

    def test_mode_switching(self):
        """Switching between text and photo mode keeps the text and only
        warns if an image is loaded."""
        res = {"warnings": 0}

        def count_and_cancel(d):
            res["warnings"] += 1
            d.OnClose(None)

        def count_and_accept(d):
            res["warnings"] += 1
            d.OnOK(None)

        def click_photo(ex, hook=None):
            """Clicking the tool toggles it first, then calls the handler."""
            tool_id = ex.photoTool.Id
            ex.toolbar.ToggleTool(tool_id, not ex.toolbar.GetToolState(tool_id))
            return ex.OnPhoto(None, hook)

        def play(ex, app):
            def fun():
                try:
                    ex.input_text_field.SetValue("Kept text")

                    # Text -> photo: no warning, text is kept
                    res["to_photo"] = click_photo(ex, count_and_cancel)
                    res["drop_shown"] = ex.image_drop_space.IsShown()
                    res["text_1"] = ex.input_text_field.GetValue()

                    # Photo without image -> text: no warning, text is kept
                    res["to_text"] = click_photo(ex, count_and_cancel)
                    res["drop_hidden"] = not ex.image_drop_space.IsShown()
                    res["text_2"] = ex.input_text_field.GetValue()
                    res["warnings_no_img"] = res["warnings"]

                    # Photo with image -> text: warning, cancel keeps everything
                    click_photo(ex)
                    ex.fileDrop.loadedFile = TEST_IMG
                    ex.set_img_with_date(TEST_IMG, wx.DateTime(2, 11, 2020, 5, 31))
                    res["cancel"] = click_photo(ex, count_and_cancel)
                    res["img_after_cancel"] = ex.imgLoaded
                    res["tool_after_cancel"] = ex.toolbar.GetToolState(ex.photoTool.Id)

                    # Accepting drops the image but keeps the text
                    res["accept"] = click_photo(ex, count_and_accept)
                    res["tool_after_accept"] = ex.toolbar.GetToolState(ex.photoTool.Id)
                    res["img_after_accept"] = ex.imgLoaded
                    res["text_3"] = ex.input_text_field.GetValue()
                    res["warnings_total"] = res["warnings"]
                finally:
                    ex.input_text_field.Clear()
                    ex.imgLoaded = False
                    ex.OnX(None)

            wx.CallAfter(fun)
            app.MainLoop()
            app.Destroy()

        self.run_in_test_dir(play)

        assert res["to_photo"] == 0 and res["to_text"] == 0
        assert res["drop_shown"] and res["drop_hidden"]
        assert res["text_1"] == res["text_2"] == res["text_3"] == "Kept text"
        assert res["warnings_no_img"] == 0
        assert res["cancel"] == -1 and res["img_after_cancel"]
        assert res["tool_after_cancel"]
        assert res["accept"] == 0 and not res["img_after_accept"]
        assert not res["tool_after_accept"]
        assert res["warnings_total"] == 2

    def test_keyboard_shortcuts(self):
        res = {}

        def send_key(ex, key, ctrl=False, alt=False):
            evt = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
            evt.SetKeyCode(key)
            evt.SetControlDown(ctrl)
            evt.SetAltDown(alt)
            return ex.GetEventHandler().ProcessEvent(evt)

        def preview(ex):
            return ex.fix_text_box.LabelText

        def play(ex, app):
            def fun():
                try:
                    # Ctrl+S saves the entries
                    for text, month in [("First entry", 2), ("Second entry", 5)]:
                        ex.update_date(wx.DateTime(1, month, 2020, 10))
                        ex.input_text_field.SetValue(text)
                        res[f"save_{month}"] = send_key(ex, ord("S"), ctrl=True)
                        res[f"cleared_{month}"] = ex.input_text_field.GetValue() == ""

                    # Alt+arrows go through the entries
                    res["last"] = "Second entry" in preview(ex)
                    send_key(ex, wx.WXK_LEFT, alt=True)
                    res["prev"] = "First entry" in preview(ex)
                    send_key(ex, wx.WXK_RIGHT, alt=True)
                    res["next"] = "Second entry" in preview(ex)

                    # Ctrl+P toggles the photo mode
                    send_key(ex, ord("P"), ctrl=True)
                    res["photo_on"] = ex.image_drop_space.IsShown()
                    send_key(ex, ord("P"), ctrl=True)
                    res["photo_off"] = not ex.image_drop_space.IsShown()

                    # Other keys are passed on
                    res["other"] = send_key(ex, ord("X"))
                    res["other_ctrl"] = send_key(ex, ord("X"), ctrl=True)
                finally:
                    # Ctrl+Q closes the app
                    res["quit"] = send_key(ex, ord("Q"), ctrl=True)

            wx.CallAfter(fun)
            app.MainLoop()
            app.Destroy()

        self.run_in_test_dir(play)

        assert res["save_2"] and res["save_5"]
        assert res["cleared_2"] and res["cleared_5"]
        assert res["last"] and res["prev"] and res["next"]
        assert res["photo_on"] and res["photo_off"]
        assert not res["other"] and not res["other_ctrl"]
        assert res["quit"]


class TestShortcutFor(TestCase):
    def test_ctrl_shortcuts(self):
        for letter, action in [
            ("S", "save"),
            ("P", "photo"),
            ("D", "date"),
            ("O", "folder"),
            ("T", "selfie"),
            ("Q", "quit"),
        ]:
            for in_text in (True, False):
                for code in (ord(letter), ord(letter.lower())):
                    assert shortcut_for(code, True, False, False, in_text) == action
            # Not without Ctrl, nor with Shift or Alt
            assert shortcut_for(ord(letter), False, False, False, False) is None
            assert shortcut_for(ord(letter), True, False, True, False) is None
            assert shortcut_for(ord(letter), True, True, False, False) is None
        assert shortcut_for(ord("X"), True, False, False, False) is None

    def test_arrows(self):
        left, right = wx.WXK_LEFT, wx.WXK_RIGHT
        # Plain arrows move the cursor in the text input
        assert shortcut_for(left, False, False, False, True) is None
        assert shortcut_for(right, False, False, False, True) is None
        # Elsewhere they go through the entries
        assert shortcut_for(left, False, False, False, False) == "prev"
        assert shortcut_for(right, False, False, False, False) == "next"
        # With Alt they always do
        assert shortcut_for(left, False, True, False, True) == "prev"
        assert shortcut_for(right, False, True, False, True) == "next"
        # Ctrl+arrows (word jump) and Shift+arrows (selection) are left alone
        assert shortcut_for(left, True, False, False, True) is None
        assert shortcut_for(right, False, False, True, False) is None
