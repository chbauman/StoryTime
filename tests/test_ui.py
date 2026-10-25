"""Tests of the main window with the controller, using fake dialogs.

The logic is tested in `test_controller.py`. Here it is checked that the widgets
show what the controller says and that the tools and the keys reach it.
"""

import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from unittest import TestCase

import wx

from story_time import settings
from story_time.main import main
from story_time.shortcuts import KEY_LEFT, KEY_RIGHT
from story_time.texts import tr
from story_time.user_interface import (
    LOGO_MARGIN,
    TOOL_SIZE,
    StoryTimeAppUI,
    month_label,
)
from story_time.util import icon_path
from tests.fakes import FakeDialogs
from tests.helpers import (
    DATA_DIR,
    SAMPLE_IMG_DIR,
    LazyStore,
    create_test_dirs,
    img_dir,
    use_data_dir,
)

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")
STORE = LazyStore()


def seed_entries():
    """Puts entries of two months, a photo and a missing photo into the folder."""
    shutil.copy(TEST_IMG, os.path.join(img_dir, "IMG_1.jpg"))
    STORE.save_entry("Walk by the lake\n\nsecond line", datetime(2020, 10, 22, 21, 32))
    STORE.save_entry(
        "Logo sketch", datetime(2020, 10, 20, 18, 15), "photo", "IMG_1.jpg"
    )
    STORE.save_entry("Lost photo", datetime(2020, 10, 19, 10), "photo", "missing.jpg")
    STORE.save_entry("Spring", datetime(2020, 3, 3, 7, 30))


@contextmanager
def main_window(seed=seed_entries, dialogs=None):
    """The main window in the test folder, with fake dialogs."""
    with use_data_dir(DATA_DIR), create_test_dirs():
        if seed is not None:
            seed()
        app = wx.App()
        dialogs = FakeDialogs() if dialogs is None else dialogs
        frame = StoryTimeAppUI(None, dialogs)

        # Windows are only deleted later by the event loop, so note the cleanup
        frame.closed = False
        cleanup = frame.cleanup

        def tracked_cleanup():
            frame.closed = True
            cleanup()

        frame.cleanup = tracked_cleanup
        try:
            yield frame, dialogs
        finally:
            if not frame.closed:
                frame.cleanup()
            # A destroyed window is only removed from the top-level windows when
            # the event loop is idle. Do that, so the next test starts clean.
            app.Yield()
            app.Destroy()


def click(frame, tool):
    """Clicks a tool of the toolbar, which toggles it first if it can be toggled."""
    toolbar = frame.toolbar
    if tool.CanBeToggled():
        toolbar.ToggleTool(tool.Id, not toolbar.GetToolState(tool.Id))
    event = wx.CommandEvent(wx.wxEVT_TOOL, tool.Id)
    toolbar.GetEventHandler().ProcessEvent(event)


def press(frame, key, ctrl=False, alt=False):
    """Presses a key in the window, returns whether it was used."""
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(key)
    event.SetControlDown(ctrl)
    event.SetAltDown(alt)
    return frame.GetEventHandler().ProcessEvent(event)


def tree_texts(tree: wx.TreeCtrl, item=None) -> list:
    """The texts of the children of the item, of the root by default."""
    item = tree.GetRootItem() if item is None else item
    texts = []
    child, cookie = tree.GetFirstChild(item)
    while child.IsOk():
        texts.append(tree.GetItemText(child))
        child, cookie = tree.GetNextChild(item, cookie)
    return texts


def find(frame, text):
    return next(e for e in frame.controller.entries if e.text.startswith(text))


def tool_state(frame):
    """Whether the tool to write is toggled."""
    return frame.toolbar.GetToolState(frame.new_tool.Id)


def press_button(button):
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON))


def click_tool(frame, tool):
    """Clicks a tool of the toolbar that is not toggled, if it is enabled."""
    if frame.toolbar.GetToolEnabled(tool.Id):
        event = wx.CommandEvent(wx.wxEVT_TOOL, tool.Id)
        frame.toolbar.GetEventHandler().ProcessEvent(event)


def list_texts(frame):
    return [e.first_line for e, _ in frame.entry_list.shown if e.deleted_at is None]


def trash_texts(frame):
    return [e.first_line for e, _ in frame.entry_list.shown if e.deleted_at]


class TestStart(TestCase):
    def test_starts_writing(self):
        with main_window() as (frame, dialogs):
            assert frame.book.GetSelection() == frame.EDIT_PAGE
            assert tool_state(frame) is True
            # The image area is always there, with the buttons to fill it
            assert frame.image_drop_space.IsShown()
            assert frame.upload_button.IsShown() and frame.selfie_button.IsShown()
            assert not frame.remove_image_button.IsShown()
            assert not frame.toolbar.GetToolEnabled(frame.undo_tool.Id)
            assert not frame.toolbar.GetToolEnabled(frame.redo_tool.Id)
            assert frame.input_text_field.GetValue() == ""
            assert not dialogs.confirms and dialogs.folder_asked == 0
            assert frame.GetTitle() == tr("app.title")
            # The date is shown
            assert frame.date_label.GetLabel().startswith("Date: ")
            # The data folder is in the tooltip of the folder tool
            tip = frame.toolbar.GetToolShortHelp(frame.folder_tool.Id)
            assert DATA_DIR in tip and "Ctrl+O" in tip

    def test_without_a_folder_the_app_does_not_start(self):
        with use_data_dir(DATA_DIR):
            settings.save_settings({})
            app = wx.App()
            try:
                with self.assertRaises(SystemExit):
                    StoryTimeAppUI(None, FakeDialogs())
            finally:
                app.Destroy()

    def test_main_function(self):
        with use_data_dir(DATA_DIR), create_test_dirs():
            # The main loop ends with the last window. Make sure it ends anyway.
            main(lambda frame: (frame.Close(), wx.CallAfter(wx.GetApp().ExitMainLoop)))

    def test_key_codes_are_the_ones_of_wx(self):
        assert KEY_LEFT == wx.WXK_LEFT and KEY_RIGHT == wx.WXK_RIGHT

    def test_image_size(self):
        size = StoryTimeAppUI.image_size
        assert size(wx.Size(900, 500)) == 270  # a third of the width
        assert size(wx.Size(3000, 200)) == 170  # the height
        assert size(wx.Size(3000, 3000)) == 370  # at most the maximum
        assert size(wx.Size(60, 500)) == 0  # too small
        assert size(wx.Size(0, 0)) == 0


class TestEntryList(TestCase):
    def test_list_of_entries(self):
        with main_window() as (frame, _):
            tree = frame.entry_list.tree
            months = tree_texts(tree)
            first_month = tree.GetFirstChild(tree.GetRootItem())[0]
            rows = tree_texts(tree, first_month)
            expanded = [
                tree.IsExpanded(first_month),
                tree.IsExpanded(tree.GetNextSibling(first_month)),
            ]
            info = frame.entry_list.info.GetLabel()
        # The trash is at the bottom, closed
        assert months == [
            month_label(2020, 10),
            month_label(2020, 3),
            tr("main.trash", count=0),
        ]
        assert len(rows) == 3 and rows[0].startswith("22.")
        assert "[Photo] Logo sketch" in rows[1] and "Lost photo" in rows[2]
        # The newest month is open, the others are closed
        assert expanded == [True, False] and info == ""

    def test_empty_list(self):
        with main_window(seed=None) as (frame, _):
            assert frame.entry_list.info.GetLabel() == "No entries yet."
            assert tree_texts(frame.entry_list.tree) == [tr("main.trash", count=0)]

    def test_search(self):
        with main_window() as (frame, _):
            lst = frame.entry_list
            lst.search.SetValue("SKETCH")
            found = [e.first_line for e, _ in lst.shown]
            expanded = lst.tree.IsExpanded(
                lst.tree.GetFirstChild(lst.tree.GetRootItem())[0]
            )
            lst.search.SetValue("zzz")
            nothing = (lst.info.GetLabel(), len(lst.shown))
            lst.search.SetValue("")
            everything = (len(lst.shown), lst.info.GetLabel())
        assert found == ["Logo sketch"] and expanded
        assert nothing == ("No matching entries.", 0)
        assert everything == (4, "")

    def test_selecting_an_entry_shows_it(self):
        with main_window() as (frame, _):
            lst = frame.entry_list
            lst.select_entry(find(frame, "Walk"), notify=True)
            page = frame.book.GetSelection()
            text = frame.fix_text_box.GetValue()
            header = frame.view_label.GetLabel()
            no_image = not frame.prev_img_space.IsShown()
            state = tool_state(frame)

            lst.select_entry(find(frame, "Logo"), notify=True)
            photo = (
                frame.fix_text_box.GetValue(),
                frame.prev_img_space.IsShown(),
                os.path.basename(frame.prev_img_name or ""),
            )
            lst.select_entry(find(frame, "Lost"), notify=True)
            lost = not frame.prev_img_space.IsShown()
            lst.select_entry(find(frame, "Spring"), notify=True)
            spring = not frame.prev_img_space.IsShown()

        assert page == frame.VIEW_PAGE and no_image
        assert text == "Walk by the lake\n\nsecond line"
        assert "22.10.2020" in header and "21:32" in header
        assert state is False
        assert photo == ("Logo sketch", True, "IMG_1.jpg")
        assert lost and spring

    def test_long_entry_is_shown_completely(self):
        paragraphs = [f"Paragraph {i}: " + "word " * 80 for i in range(1, 11)]
        entry = "\n\n".join(paragraphs)
        with main_window(seed=None) as (frame, _):
            frame.input_text_field.SetValue(entry)
            press_button(frame.save_button)
            frame.controller.set_writing(False)
            frame.controller.select_adjacent(1)
            box = frame.fix_text_box
            shown = box.GetValue()
            read_only = not box.IsEditable()
            lines = box.GetNumberOfLines()
            start = box.GetInsertionPoint()
        assert entry in shown and read_only
        # More lines than fit in the control (and independent of the width)
        assert lines >= 19 and start == 0


class TestTools(TestCase):
    def test_new_tool_switches_between_writing_and_reading(self):
        with main_window() as (frame, _):
            click(frame, frame.new_tool)
            reading = (frame.book.GetSelection(), tool_state(frame))
            click(frame, frame.new_tool)
            writing = (frame.book.GetSelection(), tool_state(frame))
        assert reading == (frame.VIEW_PAGE, False)
        assert writing == (frame.EDIT_PAGE, True)

    def test_leaving_with_unsaved_text_asks(self):
        with main_window() as (frame, dialogs):
            frame.input_text_field.SetValue("My draft")
            # Keeping it: the tool is toggled back and the page stays
            dialogs.answer_confirm(False)
            click(frame, frame.new_tool)
            kept = (frame.book.GetSelection(), tool_state(frame))
            text = frame.input_text_field.GetValue()
            # Discarding it
            dialogs.answer_confirm(True)
            click(frame, frame.new_tool)
            left = (frame.book.GetSelection(), frame.input_text_field.GetValue())
        assert kept == (frame.EDIT_PAGE, True) and text == "My draft"
        assert left == (frame.VIEW_PAGE, "")
        assert dialogs.confirms[0][0] == tr("message.discard_text.text")

    def test_selecting_an_entry_with_unsaved_text_asks(self):
        with main_window() as (frame, dialogs):
            frame.input_text_field.SetValue("My draft")
            dialogs.answer_confirm(False, True)
            frame.entry_list.select_entry(find(frame, "Walk"), notify=True)
            kept = (frame.book.GetSelection(), frame.entry_list.selected_entry())
            frame.entry_list.select_entry(find(frame, "Walk"), notify=True)
            read = (frame.book.GetSelection(), frame.entry_list.selected_entry())
        assert kept == (frame.EDIT_PAGE, None)
        assert read[0] == frame.VIEW_PAGE and read[1].text.startswith("Walk")

    def test_upload_button(self):
        with main_window() as (frame, dialogs):
            press_button(frame.upload_button)
            nothing = frame.draft_image
            dialogs.image_file = TEST_IMG
            press_button(frame.upload_button)
            shown = (
                frame.draft_image,
                frame.remove_image_button.IsShown(),
                frame.upload_button.IsShown(),
                frame.selfie_button.IsShown(),
                frame.image_drop_space.IsShown(),
            )
            press_button(frame.remove_image_button)
            again = (
                frame.remove_image_button.IsShown(),
                frame.upload_button.IsShown(),
                frame.selfie_button.IsShown(),
            )
        assert dialogs.image_file_asked == 2 and nothing is None
        # With an image it can only be removed, without one only be added
        assert shown == (TEST_IMG, True, False, False, True)
        assert again == (False, True, True)

    def test_take_image_button(self):
        with main_window() as (frame, dialogs):
            dialogs.selfie_source = TEST_IMG
            press_button(frame.selfie_button)
            result = (
                frame.remove_image_button.IsShown(),
                os.path.basename(frame.draft_image or ""),
            )
        assert result[0] and result[1].endswith("_Self.png")

    def test_selfie_without_webcam_shows_a_message(self):
        with main_window() as (frame, dialogs):
            dialogs.no_webcam = True
            press_button(frame.selfie_button)
        assert dialogs.infos[0][1] == tr("message.no_webcam.title")

    def test_remove_image_button(self):
        with main_window() as (frame, _):
            no_image = not frame.remove_image_button.IsShown()
            frame.input_text_field.SetValue("Kept text")
            frame.controller.load_image(TEST_IMG, datetime(2020, 1, 2, 3, 4, 5))
            shown = frame.remove_image_button.IsShown()
            date = frame.date_label.GetLabel()
            press_button(frame.remove_image_button)
            removed = (
                frame.draft_image,
                frame.remove_image_button.IsShown(),
                frame.image_drop_space.IsShown(),
                frame.input_text_field.GetValue(),
                frame.toolbar.GetToolEnabled(frame.undo_tool.Id),
            )
        assert no_image and shown and "2.1.2020" in date
        assert removed == (None, False, True, "Kept text", True)

    def test_discard_and_save_buttons(self):
        with main_window() as (frame, dialogs):
            press_button(frame.discard_button)
            nothing = frame.toolbar.GetToolEnabled(frame.undo_tool.Id)
            press_button(frame.save_button)  # no text
            frame.controller.draft_date = datetime(2021, 1, 2, 3, 4, 5)
            frame.input_text_field.SetValue("Brand new")
            press_button(frame.save_button)
            saved = frame.input_text_field.GetValue(), list_texts(frame)[0]
            frame.input_text_field.SetValue("My draft")
            press_button(frame.discard_button)
            discarded = frame.input_text_field.GetValue()
            first = STORE.load_all()[0]
        assert nothing is False
        assert dialogs.infos == [
            (tr("message.no_text.text"), tr("message.no_text.title"))
        ]
        assert saved == ("", "Brand new") and discarded == ""
        assert first.date_time == datetime(2021, 1, 2, 3, 4, 5)
        assert not dialogs.confirms

    def test_undo_and_redo_tools(self):
        with main_window() as (frame, _):
            frame.input_text_field.SetValue("My draft")
            press(frame, wx.WXK_ESCAPE)
            gone = frame.input_text_field.GetValue() == ""
            enabled = [
                frame.toolbar.GetToolEnabled(t.Id)
                for t in (frame.undo_tool, frame.redo_tool)
            ]
            tip = frame.toolbar.GetToolShortHelp(frame.undo_tool.Id)
            click_tool(frame, frame.undo_tool)
            back = frame.input_text_field.GetValue()
            enabled_after = [
                frame.toolbar.GetToolEnabled(t.Id)
                for t in (frame.undo_tool, frame.redo_tool)
            ]
            click_tool(frame, frame.redo_tool)
            again = frame.input_text_field.GetValue()
        assert gone and enabled == [True, False]
        assert tr("undo.draft_discarded") in tip
        assert back == "My draft" and enabled_after == [False, True]
        assert again == ""

    def test_typing_ends_the_undo_of_a_discard(self):
        with main_window() as (frame, _):
            frame.input_text_field.SetValue("My draft")
            frame.controller.discard_draft()
            frame.input_text_field.AppendText("New")
            enabled = frame.toolbar.GetToolEnabled(frame.undo_tool.Id)
        assert not enabled

    def test_date_line_opens_the_date_dialog(self):
        with main_window() as (frame, dialogs):
            dialogs.date = datetime(2021, 3, 4, 5, 6, 7)
            for widget in (frame.date_label, frame.date_label.GetParent()):
                dialogs.date_starts.clear()
                event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
                widget.GetEventHandler().ProcessEvent(event)
                assert len(dialogs.date_starts) == 1
            label = frame.date_label.GetLabel()
        assert "4.3.2021" in label and "05:06:07" in label

    def test_folder_tool(self):
        import tempfile

        with tempfile.TemporaryDirectory() as other, main_window() as (frame, dialogs):
            dialogs.folder = other
            click(frame, frame.folder_tool)
            rows = tree_texts(frame.entry_list.tree)
            info = frame.entry_list.info.GetLabel()
            tip = frame.toolbar.GetToolShortHelp(frame.folder_tool.Id)
        assert rows == [tr("main.trash", count=0)]
        assert info == "No entries yet." and other in tip

    def test_dropping_an_image(self):
        with main_window() as (frame, dialogs):
            drop = frame.text_edit_panel.file_drop
            assert drop.OnDropFiles(0, 0, [TEST_IMG])
            assert frame.draft_image == TEST_IMG
            assert not drop.OnDropFiles(0, 0, ["notes.txt"])
            # Not while reading
            dialogs.answer_confirm(True)
            frame.controller.set_writing(False)
            assert not drop.OnDropFiles(0, 0, [TEST_IMG])

    def test_clicking_an_image_shows_it_large(self):
        with main_window() as (frame, dialogs):
            frame.controller.load_image(TEST_IMG)
            event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
            frame.image_drop_space.GetEventHandler().ProcessEvent(event)

            dialogs.answer_confirm(True)  # The loaded image is lost
            frame.entry_list.select_entry(find(frame, "Logo"), notify=True)
            event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
            frame.prev_img_space.GetEventHandler().ProcessEvent(event)
        assert dialogs.photos == [
            TEST_IMG,
            os.path.join(img_dir, "IMG_1.jpg"),
        ]

    def test_the_tools_are_on_the_right_of_the_logo(self):
        with main_window() as (frame, _):
            toolbar = frame.toolbar
            tools = (
                frame.new_tool,
                frame.folder_tool,
                frame.undo_tool,
                frame.redo_tool,
            )
            positions = [toolbar.GetToolPos(t.Id) for t in tools]
        # The logo and the space that pushes the tools to the right come first
        assert positions == sorted(positions) and positions[0] >= 2

    def test_logo_and_tools_have_the_same_height(self):
        """So the bar lays them out in the same way, centered, on every platform."""
        with main_window() as (frame, _):
            logo = frame.logo.GetBitmap().GetSize()
            tool = frame.undo_tool.GetNormalBitmap().GetSize()
            disabled = frame.undo_tool.GetDisabledBitmap().GetSize()
            source = wx.Image(os.path.join(icon_path, "logo.png"))
        assert logo.height == tool.height == disabled.height == TOOL_SIZE
        assert tool.width == TOOL_SIZE and logo.width == TOOL_SIZE + 2 * LOGO_MARGIN
        # The image is much larger than what is shown, so it stays sharp
        assert source.GetWidth() >= 4 * TOOL_SIZE

    def test_disabled_tools_have_their_own_gray_icon(self):
        with main_window() as (frame, _):
            enabled = frame.undo_tool.GetNormalBitmap().ConvertToImage()
            disabled = frame.undo_tool.GetDisabledBitmap().ConvertToImage()
        assert disabled.GetSize() == enabled.GetSize()
        # Gray, and fainter than the icon
        pixels = [
            (disabled.GetRed(x, y), disabled.GetGreen(x, y), disabled.GetBlue(x, y))
            for x in range(disabled.GetWidth())
            for y in range(disabled.GetHeight())
            if disabled.GetAlpha(x, y) > 0
        ]
        assert pixels and all(r == g == b for r, g, b in pixels)
        assert max(disabled.GetAlpha()) < max(enabled.GetAlpha())


class TestEditAndDelete(TestCase):
    def read(self, frame, text):
        """Selects the entry in the list, which can be one in the trash."""
        entries = frame.controller.trash + frame.controller.entries
        entry = next(e for e in entries if e.text.startswith(text))
        frame.entry_list.select_entry(entry, notify=True)

    def action_buttons(self, frame):
        return [
            frame.edit_button.IsShown(),
            frame.delete_button.IsShown(),
            frame.restore_button.IsShown(),
            frame.delete_forever_button.IsShown(),
            frame.empty_trash_button.IsShown(),
        ]

    def test_buttons_follow_the_entry(self):
        with main_window() as (frame, _):
            writing = self.action_buttons(frame)
            click(frame, frame.new_tool)  # reading, nothing selected
            nothing = self.action_buttons(frame)
            self.read(frame, "Walk")
            entry = self.action_buttons(frame)
            frame.controller.delete_selected()
            gone = self.action_buttons(frame)
            self.read(frame, "Walk")
            trashed = self.action_buttons(frame)
        assert nothing == gone == writing == [False] * 5
        assert entry == [True, True, False, False, False]
        assert trashed == [False, False, True, True, True]

    def test_trash_is_the_last_item_of_the_list(self):
        with main_window() as (frame, _):
            self.read(frame, "Spring")
            press_button(frame.delete_button)
            tree = frame.entry_list.tree
            labels = tree_texts(tree)
            trash_item = frame.entry_list.trash_item
            closed = not tree.IsExpanded(trash_item)
            rows = tree_texts(tree, trash_item)
            self.read(frame, "Spring")
            opened = tree.IsExpanded(trash_item)
            selected = tree.GetSelection() != trash_item
        assert labels[-1] == tr("main.trash", count=1)
        assert closed and opened and selected
        assert len(rows) == 1 and rows[0].endswith("Spring")

    def test_edit_button(self):
        with main_window() as (frame, dialogs):
            self.read(frame, "Walk")
            press_button(frame.edit_button)
            editing = (
                frame.book.GetSelection(),
                frame.input_text_field.GetValue(),
                frame.discard_button.GetLabel(),
                frame.date_label.GetLabel(),
            )
            frame.input_text_field.SetValue("Edited walk")
            dialogs.answer_confirm(True)
            press_button(frame.discard_button)
        assert editing[0] == frame.EDIT_PAGE
        assert editing[1].startswith("Walk by the lake")
        assert editing[2] == tr("main.cancel_edit")
        assert editing[3].startswith(tr("main.editing_line", date="")[:8])

    def test_save_changes_the_entry_in_the_list(self):
        with main_window() as (frame, _):
            self.read(frame, "Spring")
            press_button(frame.edit_button)
            frame.input_text_field.SetValue("Late spring")
            press_button(frame.save_button)
            page = frame.book.GetSelection()
            shown = frame.view_label.GetLabel(), frame.fix_text_box.GetValue()
            selected = frame.entry_list.selected_entry()
            texts = list_texts(frame)
            label = frame.discard_button.GetLabel()
        assert page == frame.VIEW_PAGE and shown[1] == "Late spring"
        assert selected.text == "Late spring" and "Late spring" in texts
        assert "Spring" not in texts
        assert label == tr("main.discard")

    def test_cancel_button_asks_about_changes(self):
        with main_window() as (frame, dialogs):
            self.read(frame, "Spring")
            press_button(frame.edit_button)
            frame.input_text_field.SetValue("Changed")
            dialogs.answer_confirm(False, True)
            press_button(frame.discard_button)
            kept = frame.book.GetSelection()
            press_button(frame.discard_button)
            read = (frame.book.GetSelection(), frame.fix_text_box.GetValue())
        assert kept == frame.EDIT_PAGE
        assert read == (frame.VIEW_PAGE, "Spring")

    def test_edit_shortcut(self):
        with main_window() as (frame, _):
            self.read(frame, "Walk")
            press(frame, ord("E"), ctrl=True)
            assert frame.book.GetSelection() == frame.EDIT_PAGE

    def test_delete_button_and_undo(self):
        with main_window() as (frame, dialogs):
            self.read(frame, "Spring")
            press_button(frame.delete_button)
            deleted = (
                list_texts(frame),
                trash_texts(frame),
                frame.toolbar.GetToolEnabled(frame.undo_tool.Id),
                frame.toolbar.GetToolShortHelp(frame.undo_tool.Id),
            )
            click_tool(frame, frame.undo_tool)
            back = (list_texts(frame), frame.fix_text_box.GetValue())
            click_tool(frame, frame.redo_tool)
            again = list_texts(frame), trash_texts(frame)
        assert "Spring" not in deleted[0] and deleted[1] == ["Spring"]
        assert deleted[2] and tr("undo.entry_deleted") in deleted[3]
        assert "Spring" in back[0] and back[1] == "Spring"
        assert "Spring" not in again[0] and again[1] == ["Spring"]
        assert not dialogs.confirms

    def test_typing_does_not_end_the_undo_of_a_deletion(self):
        with main_window() as (frame, _):
            self.read(frame, "Spring")
            press_button(frame.delete_button)
            click(frame, frame.new_tool)
            frame.input_text_field.AppendText("Typing")
            assert frame.toolbar.GetToolEnabled(frame.undo_tool.Id)

    def test_restore_button(self):
        with main_window() as (frame, _):
            self.read(frame, "Spring")
            press_button(frame.delete_button)
            self.read(frame, "Spring")
            press_button(frame.restore_button)
            texts = list_texts(frame), trash_texts(frame)
            label = tree_texts(frame.entry_list.tree)[-1]
        assert "Spring" in texts[0] and texts[1] == []
        assert label == tr("main.trash", count=0)

    def test_delete_for_good_and_empty_trash_ask(self):
        with main_window() as (frame, dialogs):
            for text in ("Spring", "Logo"):
                self.read(frame, text)
                press_button(frame.delete_button)
            self.read(frame, "Spring")
            dialogs.answer_confirm(True)
            press_button(frame.delete_forever_button)
            one_left = trash_texts(frame)
            self.read(frame, "Logo")
            dialogs.answer_confirm(False, True)
            press_button(frame.empty_trash_button)
            kept = trash_texts(frame)
            press_button(frame.empty_trash_button)
            empty = trash_texts(frame)
        assert one_left == ["Logo sketch"] and kept == ["Logo sketch"]
        assert empty == []
        assert not os.path.exists(os.path.join(img_dir, "IMG_1.jpg"))


class TestKeys(TestCase):
    def test_keyboard_shortcuts(self):
        with main_window(seed=None) as (frame, dialogs):
            # Ctrl+S saves the entries
            for text, date in [
                ("First entry", datetime(2020, 3, 1, 10)),
                ("Second entry", datetime(2020, 6, 1, 10)),
            ]:
                frame.controller.draft_date = date
                frame.input_text_field.SetValue(text)
                assert press(frame, ord("S"), ctrl=True)
                assert frame.input_text_field.GetValue() == ""
            entries = len(frame.controller.entries)

            # Ctrl+N leaves the writing, Ctrl+S then does not save
            press(frame, ord("N"), ctrl=True)
            reading = frame.book.GetSelection() == frame.VIEW_PAGE
            frame.input_text_field.SetValue("Not saved")
            press(frame, ord("S"), ctrl=True)
            not_saved = len(frame.controller.entries) == entries
            frame.input_text_field.Clear()

            # Alt+arrows go through the entries, older ones are "previous"
            press(frame, KEY_LEFT, alt=True)
            newest = frame.fix_text_box.GetValue()
            press(frame, KEY_LEFT, alt=True)
            older = frame.fix_text_box.GetValue()
            press(frame, KEY_LEFT, alt=True)
            oldest_stays = frame.fix_text_box.GetValue()
            press(frame, KEY_RIGHT, alt=True)
            newer = frame.fix_text_box.GetValue()
            selected = frame.entry_list.selected_entry().text

            # Ctrl+N again to write, then Ctrl+P asks for an image to upload
            press(frame, ord("N"), ctrl=True)
            writing = frame.book.GetSelection() == frame.EDIT_PAGE
            press(frame, ord("P"), ctrl=True)
            asked = dialogs.image_file_asked

            # Other keys are passed on
            other = (press(frame, ord("X")), press(frame, ord("X"), ctrl=True))

            # Ctrl+Q closes the window
            quit_used = press(frame, ord("Q"), ctrl=True)
            closed = frame.closed

        assert entries == 2 and reading and not_saved
        assert newest == "Second entry" and older == "First entry"
        assert oldest_stays == "First entry" and newer == "Second entry"
        assert selected == "Second entry"
        assert writing and asked == 1
        assert other == (False, False)
        assert quit_used and closed
        assert not dialogs.confirms

    def test_keys_for_date_folder_and_selfie(self):
        with main_window() as (frame, dialogs):
            press(frame, ord("D"), ctrl=True)
            press(frame, ord("O"), ctrl=True)
            press(frame, ord("T"), ctrl=True)
        assert len(dialogs.date_starts) == 1
        assert dialogs.folder_asked == 1
        assert len(dialogs.selfie_targets) == 1


class TestClosing(TestCase):
    def test_close_without_a_draft(self):
        with main_window() as (frame, dialogs):
            frame.Close()
            closed = frame.closed
        assert closed and not dialogs.confirms

    def test_close_with_a_draft_asks(self):
        with main_window() as (frame, dialogs):
            frame.input_text_field.SetValue("My draft")
            dialogs.answer_confirm(False)
            frame.Close()
            kept_open = not frame.closed
            dialogs.answer_confirm(True)
            frame.Close()
            closed = frame.closed
        assert kept_open and closed

    def test_closing_saves_the_folder_and_cleans_up(self):
        with main_window() as (frame, _):
            temp = frame.controller.temp.path
            settings.save_settings({})
            frame.Close()
            assert not os.path.exists(temp)
            assert settings.get_data_dir() == DATA_DIR
