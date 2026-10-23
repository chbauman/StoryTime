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

from story_time import folders, settings
from story_time.main import main
from story_time.shortcuts import KEY_LEFT, KEY_RIGHT
from story_time.texts import tr
from story_time.user_interface import StoryTimeAppUI, month_label
from story_time.XML_write import load_all_entries, save_entry
from tests.fakes import FakeDialogs
from tests.helpers import DATA_DIR, SAMPLE_IMG_DIR, create_test_dirs, use_data_dir

TEST_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")


def seed_entries():
    """Puts entries of two months, a photo and a missing photo into the folder."""
    shutil.copy(TEST_IMG, os.path.join(folders.img_folder, "IMG_1.jpg"))
    save_entry("Walk by the lake\n\nsecond line", datetime(2020, 10, 22, 21, 32))
    save_entry("Logo sketch", datetime(2020, 10, 20, 18, 15), "photo", "IMG_1.jpg")
    save_entry("Lost photo", datetime(2020, 10, 19, 10), "photo", "missing.jpg")
    save_entry("Spring", datetime(2020, 3, 3, 7, 30))


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
        cleanup = frame.Cleanup

        def tracked_cleanup():
            frame.closed = True
            cleanup()

        frame.Cleanup = tracked_cleanup
        try:
            yield frame, dialogs
        finally:
            if not frame.closed:
                frame.Cleanup()
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
    toolbar = frame.toolbar
    return (
        toolbar.GetToolState(frame.new_tool.Id),
        [toolbar.GetToolEnabled(t.Id) for t in frame.edit_tools],
    )


class TestStart(TestCase):
    def test_starts_writing(self):
        with main_window() as (frame, dialogs):
            assert frame.book.GetSelection() == frame.EDIT_PAGE
            assert tool_state(frame) == (True, [True] * 4)
            assert frame.toolbar.GetToolState(frame.photoTool.Id) is False
            assert not frame.image_drop_space.IsShown()
            assert frame.input_text_field.GetValue() == ""
            assert not dialogs.confirms and dialogs.folder_asked == 0
            assert frame.GetTitle() == tr("app.title")
            # The date is shown
            assert frame.dateLabel.GetLabel().startswith("Date: ")
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
            main(lambda frame: frame.Close())

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
        assert months == [month_label(2020, 10), month_label(2020, 3)]
        assert len(rows) == 3 and rows[0].startswith("22.")
        assert "[Photo] Logo sketch" in rows[1] and "Lost photo" in rows[2]
        # The newest month is open, the others are closed
        assert expanded == [True, False] and info == ""

    def test_empty_list(self):
        with main_window(seed=None) as (frame, _):
            assert frame.entry_list.info.GetLabel() == "No entries yet."
            assert tree_texts(frame.entry_list.tree) == []

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
        assert state == (False, [False] * 4)  # The tools to write are disabled
        assert photo == ("Logo sketch", True, "IMG_1.jpg")
        assert lost and spring

    def test_long_entry_is_shown_completely(self):
        paragraphs = [f"Paragraph {i}: " + "word " * 80 for i in range(1, 11)]
        entry = "\n\n".join(paragraphs)
        with main_window(seed=None) as (frame, _):
            frame.input_text_field.SetValue(entry)
            click(frame, frame.edit_tools[0])  # The save tool
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
    @staticmethod
    def tools(frame):
        toolbar_tools = {t.Id: t for t in frame.edit_tools}
        save, photo, date, selfie = frame.edit_tools
        assert photo is frame.photoTool and len(toolbar_tools) == 4
        return save, photo, date, selfie

    def test_new_tool_switches_between_writing_and_reading(self):
        with main_window() as (frame, _):
            click(frame, frame.new_tool)
            reading = (frame.book.GetSelection(), tool_state(frame))
            click(frame, frame.new_tool)
            writing = (frame.book.GetSelection(), tool_state(frame))
        assert reading == (frame.VIEW_PAGE, (False, [False] * 4))
        assert writing == (frame.EDIT_PAGE, (True, [True] * 4))

    def test_unsaved_text_is_asked_about(self):
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
        assert kept == (frame.EDIT_PAGE, (True, [True] * 4)) and text == "My draft"
        assert left == (frame.VIEW_PAGE, "")
        assert dialogs.confirms[0][0] == tr("message.discard_text.text")

    def test_selecting_an_entry_with_unsaved_text_is_asked_about(self):
        with main_window() as (frame, dialogs):
            frame.input_text_field.SetValue("My draft")
            dialogs.answer_confirm(False)
            frame.entry_list.select_entry(find(frame, "Walk"), notify=True)
            kept = (frame.book.GetSelection(), frame.entry_list.selected_entry())
        assert kept == (frame.EDIT_PAGE, None)

    def test_photo_tool_shows_the_image_area_and_keeps_the_text(self):
        with main_window() as (frame, dialogs):
            _, photo, *_ = frame.edit_tools
            frame.input_text_field.SetValue("Kept text")
            click(frame, photo)
            on = frame.image_drop_space.IsShown()
            click(frame, photo)
            off = not frame.image_drop_space.IsShown()
            text = frame.input_text_field.GetValue()
        assert on and off and text == "Kept text"
        assert not dialogs.confirms

    def test_leaving_the_photo_mode_with_an_image_is_asked_about(self):
        with main_window() as (frame, dialogs):
            _, photo, *_ = frame.edit_tools
            click(frame, photo)
            assert frame.controller.load_image(TEST_IMG, datetime(2020, 1, 2, 3, 4, 5))
            shown = frame.draft_image == TEST_IMG
            date = frame.dateLabel.GetLabel()

            dialogs.answer_confirm(False)
            click(frame, photo)
            kept = (
                frame.toolbar.GetToolState(photo.Id),
                frame.image_drop_space.IsShown(),
                frame.draft_image,
            )
            dialogs.answer_confirm(True)
            click(frame, photo)
            discarded = (frame.image_drop_space.IsShown(), frame.draft_image)
        assert shown and "2.1.2020" in date
        assert kept == (True, True, TEST_IMG)
        assert discarded == (False, None)

    def test_save_tool(self):
        with main_window() as (frame, dialogs):
            save = frame.edit_tools[0]
            click(frame, save)  # no text
            frame.controller.draft_date = datetime(2021, 1, 2, 3, 4, 5)
            frame.input_text_field.SetValue("Brand new")
            click(frame, save)
            text = frame.input_text_field.GetValue()
            rows = [e.first_line for e, _ in frame.entry_list.shown]
            entries = load_all_entries()
        assert dialogs.infos == [
            (tr("message.no_text.text"), tr("message.no_text.title"))
        ]
        assert text == "" and rows[0] == "Brand new" and len(rows) == 5
        assert entries[0].date_time == datetime(2021, 1, 2, 3, 4, 5)

    def test_date_tool(self):
        with main_window() as (frame, dialogs):
            dialogs.date = datetime(2021, 3, 4, 5, 6, 7)
            click(frame, frame.edit_tools[2])
            label = frame.dateLabel.GetLabel()
        assert "4.3.2021" in label and "05:06:07" in label

    def test_selfie_tool(self):
        with main_window() as (frame, dialogs):
            dialogs.selfie_source = TEST_IMG
            click(frame, frame.edit_tools[3])
            result = (
                frame.toolbar.GetToolState(frame.photoTool.Id),
                frame.image_drop_space.IsShown(),
                os.path.basename(frame.draft_image or ""),
            )
        assert result[:2] == (True, True) and result[2].endswith("_Self.png")

    def test_selfie_without_webcam_shows_a_message(self):
        with main_window() as (frame, dialogs):
            dialogs.no_webcam = True
            click(frame, frame.edit_tools[3])
        assert dialogs.infos[0][1] == tr("message.no_webcam.title")

    def test_folder_tool(self):
        import tempfile

        with tempfile.TemporaryDirectory() as other:
            with main_window() as (frame, dialogs):
                dialogs.folder = other
                click(frame, frame.folder_tool)
                rows = tree_texts(frame.entry_list.tree)
                info = frame.entry_list.info.GetLabel()
                tip = frame.toolbar.GetToolShortHelp(frame.folder_tool.Id)
        assert rows == [] and info == "No entries yet." and other in tip

    def test_dropping_an_image(self):
        with main_window() as (frame, _):
            drop = frame.text_edit_panel.fileDrop
            # The image area is not there before the photo mode
            assert not drop.OnDropFiles(0, 0, [TEST_IMG])
            click(frame, frame.photoTool)
            assert drop.OnDropFiles(0, 0, [TEST_IMG])
            assert frame.draft_image == TEST_IMG
            assert not drop.OnDropFiles(0, 0, ["notes.txt"])

    def test_clicking_an_image_shows_it_large(self):
        with main_window() as (frame, dialogs):
            click(frame, frame.photoTool)
            frame.controller.load_image(TEST_IMG)
            event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
            frame.image_drop_space.GetEventHandler().ProcessEvent(event)

            dialogs.answer_confirm(True)  # The loaded image is lost
            frame.entry_list.select_entry(find(frame, "Logo"), notify=True)
            event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
            frame.prev_img_space.GetEventHandler().ProcessEvent(event)
        assert dialogs.photos == [
            TEST_IMG,
            os.path.join(DATA_DIR, "Img", "IMG_1.jpg"),
        ]


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

            # Ctrl+N again to write, then Ctrl+P toggles the photo mode
            press(frame, ord("N"), ctrl=True)
            writing = frame.book.GetSelection() == frame.EDIT_PAGE
            press(frame, ord("P"), ctrl=True)
            photo_on = frame.image_drop_space.IsShown()
            press(frame, ord("P"), ctrl=True)
            photo_off = not frame.image_drop_space.IsShown()

            # Other keys are passed on
            other = (press(frame, ord("X")), press(frame, ord("X"), ctrl=True))

            # Ctrl+Q closes the window
            quit_used = press(frame, ord("Q"), ctrl=True)
            closed = frame.closed

        assert entries == 2 and reading and not_saved
        assert newest == "Second entry" and older == "First entry"
        assert oldest_stays == "First entry" and newer == "Second entry"
        assert selected == "Second entry"
        assert writing and photo_on and photo_off
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
            temp = folders.get_temp_folder()
            settings.save_settings({})
            frame.Close()
            assert not os.path.exists(temp)
            assert settings.get_data_dir() == DATA_DIR
