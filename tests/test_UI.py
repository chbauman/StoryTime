import os
import shutil
import tempfile
from datetime import datetime
from unittest import TestCase

import wx

from story_time import folders
from story_time.main import main
from story_time.user_interface import StoryTimeAppUI, month_label, shortcut_for
from story_time.XML_write import save_entry
from tests.helpers import DATA_DIR, SAMPLE_IMG_DIR, create_test_dirs, use_data_dir
from tests.test_util import replace_dir_ask

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


def run_in_test_dir(play, seed=None):
    """Creates the app using the test data folder and plays with it.

    Args:
        play: Called with the frame and the app, has to run the main loop.
        seed: Called before the app is created, to put entries into the folder.
    """
    with use_data_dir(DATA_DIR):
        with create_test_dirs():
            if seed is not None:
                seed()
            app = wx.App()
            ex = StoryTimeAppUI(None)
            play(ex, app)


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

            # Leave the writing (without a webcam there is unsaved text, discard it)
            # and go through the list of the entries
            ex.toolbar.ToggleTool(ex.new_tool.Id, False)
            ex.OnNew(None, self.discard_text)
            ex.entry_list.select_adjacent(1)
            ex.entry_list.select_adjacent(1)
            ex.entry_list.select_adjacent(-1)
            ex.entry_list.select_adjacent(-1)
            ex.entry_list.select_adjacent(-1)

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
                return folders.data_path

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
        run_in_test_dir(play)

    def test_main_func(self):
        def close(d):
            d.OnX(None)

        with use_data_dir(DATA_DIR):
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

        def shown(ex):
            return ex.fix_text_box.GetValue()

        def play(ex, app):
            def fun():
                try:
                    # Ctrl+S saves the entries
                    for text, month in [("First entry", 2), ("Second entry", 5)]:
                        ex.update_date(wx.DateTime(1, month, 2020, 10))
                        ex.input_text_field.SetValue(text)
                        res[f"save_{month}"] = send_key(ex, ord("S"), ctrl=True)
                        res[f"cleared_{month}"] = ex.input_text_field.GetValue() == ""
                    res["entries"] = len(ex.entry_list.entries)

                    # Ctrl+N leaves the writing, Ctrl+S then does not save
                    send_key(ex, ord("N"), ctrl=True)
                    res["reading"] = not ex.editing
                    ex.input_text_field.SetValue("Not saved")
                    send_key(ex, ord("S"), ctrl=True)
                    res["not_saved"] = len(ex.entry_list.entries) == res["entries"]
                    ex.input_text_field.Clear()

                    # Alt+arrows go through the entries, older ones are "previous"
                    send_key(ex, wx.WXK_LEFT, alt=True)
                    res["newest"] = "Second entry" in shown(ex)
                    send_key(ex, wx.WXK_LEFT, alt=True)
                    res["prev"] = "First entry" in shown(ex)
                    send_key(ex, wx.WXK_LEFT, alt=True)
                    res["oldest_stays"] = "First entry" in shown(ex)
                    send_key(ex, wx.WXK_RIGHT, alt=True)
                    res["next"] = "Second entry" in shown(ex)

                    # Ctrl+N again to write, then Ctrl+P toggles the photo mode
                    send_key(ex, ord("N"), ctrl=True)
                    res["writing"] = ex.editing
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
        assert res["entries"] == 2
        assert res["reading"] and res["not_saved"]
        assert res["newest"] and res["prev"] and res["oldest_stays"] and res["next"]
        assert res["writing"] and res["photo_on"] and res["photo_off"]
        assert not res["other"] and not res["other_ctrl"]
        assert res["quit"]

    def test_long_entry_preview(self):
        """The preview shows long entries completely, with their line breaks."""
        paragraphs = [f"Paragraph {i}: " + "word " * 80 for i in range(1, 11)]
        entry = "\n\n".join(paragraphs)
        res = {}

        def play(ex, app):
            def fun():
                try:
                    ex.update_date(wx.DateTime(1, 2, 2020, 10))
                    ex.input_text_field.SetValue(entry)
                    ex.OnSave(None)
                    ex.toggle_new_entry()
                    ex.entry_list.select_adjacent(1)
                    res["preview"] = ex.fix_text_box.GetValue()
                    res["editable"] = ex.fix_text_box.IsEditable()
                    res["lines"] = ex.fix_text_box.GetNumberOfLines()
                    res["start"] = ex.fix_text_box.GetInsertionPoint()
                finally:
                    ex.OnX(None)

            wx.CallAfter(fun)
            app.MainLoop()
            app.Destroy()

        self.run_in_test_dir(play)

        assert entry in res["preview"]
        assert not res["editable"]
        # More lines than fit in the control (and independent of the width)
        assert res["lines"] >= 19
        assert res["start"] == 0


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


def discard_hook(d):
    d.OnOK(None)


def keep_hook(d):
    d.OnClose(None)


def tree_texts(tree: wx.TreeCtrl, item=None) -> list:
    """The texts of the children of the item, of the root by default."""
    item = tree.GetRootItem() if item is None else item
    texts = []
    child, cookie = tree.GetFirstChild(item)
    while child.IsOk():
        texts.append(tree.GetItemText(child))
        child, cookie = tree.GetNextChild(item, cookie)
    return texts


def seed_entries():
    """Puts entries of two months, a photo and a missing photo into the folder."""
    folders.update_folder(DATA_DIR)
    shutil.copy(TEST_IMG, os.path.join(DATA_DIR, "Img", "IMG_1.jpg"))
    save_entry("Walk by the lake\n\nsecond line", datetime(2020, 10, 22, 21, 32))
    save_entry("Logo sketch", datetime(2020, 10, 20, 18, 15), "photo", "IMG_1.jpg")
    save_entry("Lost photo", datetime(2020, 10, 19, 10), "photo", "missing.jpg")
    save_entry("Spring", datetime(2020, 3, 3, 7, 30))


class TestLayout(TestCase):
    """The list of the entries and switching between writing and reading."""

    @staticmethod
    def play(fun, seed=seed_entries):
        """Runs `fun(ex)` in the main loop and always closes the app after."""

        def play_it(ex, app):
            def inner():
                try:
                    fun(ex)
                finally:
                    ex.input_text_field.Clear()
                    ex.imgLoaded = False
                    ex.OnX(None)

            wx.CallAfter(inner)
            app.MainLoop()
            app.Destroy()

        run_in_test_dir(play_it, seed)

    @staticmethod
    def entry(ex, text):
        return next(e for e in ex.entry_list.entries if e.text.startswith(text))

    def test_list_of_entries(self):
        res = {}

        def fun(ex):
            lst = ex.entry_list
            res["order"] = [e.first_line for e, _ in lst.shown]
            res["months"] = tree_texts(lst.tree)
            first_month = lst.tree.GetFirstChild(lst.tree.GetRootItem())[0]
            res["first_month"] = tree_texts(lst.tree, first_month)
            res["expanded"] = [
                lst.tree.IsExpanded(c)
                for c in (
                    first_month,
                    lst.tree.GetNextSibling(first_month),
                )
            ]

            # Searching
            lst.search.SetValue("SKETCH")
            res["search"] = [e.first_line for e, _ in lst.shown]
            res["search_expanded"] = lst.tree.IsExpanded(
                lst.tree.GetFirstChild(lst.tree.GetRootItem())[0]
            )
            lst.search.SetValue("zzz")
            res["no_match"] = lst.info.GetLabel(), len(lst.shown)
            lst.search.SetValue("")
            res["all_again"] = len(lst.shown), lst.info.GetLabel()

        self.play(fun)

        assert res["order"] == [
            "Walk by the lake",
            "Logo sketch",
            "Lost photo",
            "Spring",
        ]
        assert res["months"] == [month_label(2020, 10), month_label(2020, 3)]
        assert len(res["first_month"]) == 3
        assert res["first_month"][0].startswith("22.")
        assert "[Photo] Logo sketch" in res["first_month"][1]
        # The newest month is open, the others are closed
        assert res["expanded"] == [True, False]
        assert res["search"] == ["Logo sketch"] and res["search_expanded"]
        assert res["no_match"] == ("No matching entries.", 0)
        assert res["all_again"] == (4, "")

    def test_empty_list(self):
        res = {}

        def fun(ex):
            res["info"] = ex.entry_list.info.GetLabel()
            res["tree"] = tree_texts(ex.entry_list.tree)
            ex.toggle_new_entry()
            res["nothing"] = ex.view_label.GetLabel()

        self.play(fun, seed=None)

        assert res["info"] == "No entries yet." and res["tree"] == []
        assert res["nothing"] == "Select an entry on the left or write a new one."

    def test_selecting_shows_entry(self):
        res = {}

        def fun(ex):
            lst = ex.entry_list
            res["start"] = ex.editing

            # Selecting leaves the writing, as there is nothing unsaved
            lst.select_entry(self.entry(ex, "Walk"), notify=True)
            res["reading"] = not ex.editing
            res["text"] = ex.fix_text_box.GetValue()
            res["header"] = ex.view_label.GetLabel()
            res["no_img"] = not ex.prev_img_space.IsShown()

            lst.select_entry(self.entry(ex, "Logo"), notify=True)
            res["photo_text"] = ex.fix_text_box.GetValue()
            res["photo_shown"] = ex.prev_img_space.IsShown()
            res["photo_name"] = os.path.basename(ex.prev_img_name or "")

            lst.select_entry(self.entry(ex, "Lost"), notify=True)
            res["lost_hidden"] = not ex.prev_img_space.IsShown()
            lst.select_entry(self.entry(ex, "Spring"), notify=True)
            res["text_hidden"] = not ex.prev_img_space.IsShown()
            ex.toolbar.ToggleTool(ex.new_tool.Id, True)
            ex.OnNew(None)

            # Back to writing: nothing is selected
            res["writing"] = ex.editing
            res["selection_cleared"] = lst.selected_entry() is None

        self.play(fun)

        assert res["start"] and res["reading"]
        assert res["text"] == "Walk by the lake\n\nsecond line"
        assert "22.10.2020" in res["header"] and "21:32" in res["header"]
        assert res["no_img"]
        assert res["photo_text"] == "Logo sketch"
        assert res["photo_shown"] and res["photo_name"] == "IMG_1.jpg"
        assert res["lost_hidden"] and res["text_hidden"]
        assert res["writing"] and res["selection_cleared"]

    def test_tools_depend_on_mode(self):
        res = {}

        def states(ex):
            tb = ex.toolbar
            ids = [t.Id for t in ex.edit_tools]
            return (
                tb.GetToolState(ex.new_tool.Id),
                [tb.GetToolEnabled(i) for i in ids],
                tb.GetToolEnabled(ex.folder_tool.Id),
            )

        def fun(ex):
            res["writing"] = states(ex)
            ex.toggle_new_entry()
            res["reading"] = states(ex)
            ex.toggle_new_entry()
            res["writing_again"] = states(ex)
            res["tooltip"] = ex.toolbar.GetToolShortHelp(ex.folder_tool.Id)

        self.play(fun)

        assert res["writing"] == (True, [True] * 4, True)
        assert res["reading"] == (False, [False] * 4, True)
        assert res["writing_again"] == res["writing"]
        # The data folder is shown in the tooltip of the folder tool
        assert DATA_DIR in res["tooltip"] and "Ctrl+O" in res["tooltip"]

    def test_unsaved_draft_is_not_lost(self):
        res = {}

        def fun(ex):
            lst = ex.entry_list
            walk = self.entry(ex, "Walk")

            # Keep the draft when selecting an entry
            ex.input_text_field.SetValue("My draft")
            lst.select_entry(walk)
            ex.on_entry_selected(walk, keep_hook)
            res["kept_editing"] = ex.editing
            res["kept_text"] = ex.input_text_field.GetValue()
            res["kept_selection"] = lst.selected_entry() is None

            # Discard it
            lst.select_entry(walk)
            ex.on_entry_selected(walk, discard_hook)
            res["discarded_reading"] = not ex.editing
            res["discarded_text"] = ex.input_text_field.GetValue()
            res["shown"] = ex.fix_text_box.GetValue().startswith("Walk")

            # The same when leaving the writing with the tool
            ex.toggle_new_entry()
            ex.input_text_field.SetValue("Another draft")
            ex.toolbar.ToggleTool(ex.new_tool.Id, False)
            ex.OnNew(None, keep_hook)
            res["tool_kept"] = ex.editing, ex.toolbar.GetToolState(ex.new_tool.Id)
            ex.toolbar.ToggleTool(ex.new_tool.Id, False)
            ex.OnNew(None, discard_hook)
            res["tool_left"] = ex.editing, ex.input_text_field.GetValue()

        self.play(fun)

        assert res["kept_editing"] and res["kept_text"] == "My draft"
        assert res["kept_selection"]
        assert res["discarded_reading"] and res["discarded_text"] == ""
        assert res["shown"]
        assert res["tool_kept"] == (True, True)
        assert res["tool_left"] == (False, "")

    def test_saving_updates_the_list(self):
        res = {}

        def fun(ex):
            res["before"] = len(ex.entry_list.entries)
            ex.update_date(wx.DateTime(1, 11, 2020, 12))
            ex.input_text_field.SetValue("Brand new")
            ex.OnSave(None)
            res["after"] = [e.first_line for e, _ in ex.entry_list.shown]
            res["still_writing"] = ex.editing

        self.play(fun)

        assert res["before"] == 4
        assert res["after"][0] == "Brand new" and len(res["after"]) == 5
        assert res["still_writing"]

    def test_changing_the_folder_reloads_the_list(self):
        res = {}
        other = tempfile.mkdtemp(prefix="story_time_test_other_")
        try:
            folders.update_folder(other)
            folders.create_xml_and_img_folder(other)
            save_entry("Somewhere else", datetime(2019, 1, 1, 9))
            folders.update_folder(DATA_DIR)

            def fun(ex):
                ex.toggle_new_entry()
                ex.entry_list.select_adjacent(1)
                with replace_dir_ask(lambda: other):
                    ex.OnChangeDir(None)
                res["entries"] = [e.text for e in ex.entry_list.entries]
                res["shown"] = ex.fix_text_box.GetValue()
                res["tooltip"] = ex.toolbar.GetToolShortHelp(ex.folder_tool.Id)

            self.play(fun)
        finally:
            shutil.rmtree(other, ignore_errors=True)

        assert res["entries"] == ["Somewhere else"]
        assert res["shown"] == ""
        assert other in res["tooltip"]
