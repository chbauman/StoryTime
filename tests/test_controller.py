import os
import shutil
import tempfile
from collections import deque
from contextlib import ExitStack
from datetime import datetime
from unittest import TestCase

from story_time import settings
from story_time.controller import MAX_HISTORY, DiaryController
from story_time.folders import DataFolder
from story_time.images import NEW_IMAGE
from story_time.sqlite_storage import SqliteEntryStore
from story_time.texts import tr
from tests.fakes import FakeDialogs, FakeView
from tests.helpers import (
    DATA_DIR,
    SAMPLE_IMG_DIR,
    LazyStore,
    create_test_dirs,
    img_dir,
    use_data_dir,
)

SAMPLE_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")
NOW = datetime(2026, 10, 23, 12, 0, 0)
STORE = LazyStore()


class ControllerTestCase(TestCase):
    """Starts a controller with a fake view and fake dialogs in the test folder.

    There are four entries: a text entry, a photo, a photo with a missing image
    file and an older text entry.
    """

    seed = True

    def setUp(self):
        # `TestCase.enterContext` only exists since Python 3.11
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(use_data_dir(DATA_DIR))
        stack.enter_context(create_test_dirs())
        if self.seed:
            self.seed_entries()

        self.now = NOW
        self.view = FakeView()
        self.dialogs = FakeDialogs()
        self.ctrl = DiaryController(self.view, self.dialogs, now=lambda: self.now)
        assert self.ctrl.start()
        self.addCleanup(self.ctrl.temp.remove)

    @staticmethod
    def seed_entries():
        shutil.copy(SAMPLE_IMG, os.path.join(img_dir, "IMG_1.jpg"))
        STORE.save_entry(
            "Walk by the lake\n\nsecond line", datetime(2020, 10, 22, 21, 32)
        )
        STORE.save_entry(
            "Logo sketch", datetime(2020, 10, 20, 18, 15), "photo", "IMG_1.jpg"
        )
        STORE.save_entry(
            "Lost photo", datetime(2020, 10, 19, 10), "photo", "missing.jpg"
        )
        STORE.save_entry("Spring", datetime(2020, 3, 3, 7, 30))

    def entry(self, text):
        return next(e for e in self.ctrl.entries if e.text.startswith(text))

    def texts(self, entries=None):
        entries = self.view.shown if entries is None else entries
        return [e.first_line for e in entries]

    def read(self, text):
        """Goes to reading and selects the entry."""
        self.ctrl.select_entry(self.entry(text))


class TestStart(ControllerTestCase):
    def test_initial_state(self):
        view = self.view
        assert view.folder == DATA_DIR
        assert view.editing is True
        assert view.draft_date == NOW and view.draft_image is None
        assert view.entry is None
        assert self.texts() == [
            "Walk by the lake",
            "Logo sketch",
            "Lost photo",
            "Spring",
        ]
        assert view.total == 4 and view.selected is None
        # Nothing was asked, the folder is in the settings
        assert self.dialogs.folder_asked == 0 and not self.dialogs.confirms

    def test_data_folder_is_created_and_remembered(self):
        assert self.ctrl.folder == DataFolder(DATA_DIR)
        self.ctrl.finish()
        assert settings.get_data_dir() == DATA_DIR


class TestStartWithoutFolder(TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(use_data_dir(DATA_DIR))
        self.view, self.dialogs = FakeView(), FakeDialogs()
        self.ctrl = DiaryController(self.view, self.dialogs, now=lambda: NOW)
        settings.save_settings({})

    def test_asks_for_the_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            self.dialogs.folder = folder
            assert self.ctrl.start()
            assert self.dialogs.folder_asked == 1
            assert self.view.folder == folder
            assert os.path.isdir(os.path.join(folder, "Img"))
            assert self.view.total == 0

    def test_no_folder_chosen_does_not_start(self):
        assert not self.ctrl.start()
        assert self.view.folder is None
        assert not os.path.exists("story_time.sqlite") and not os.path.exists("Img")


class TestReadingAndWriting(ControllerTestCase):
    def test_leave_writing_without_draft(self):
        self.ctrl.set_writing(False)
        assert (self.view.editing, self.ctrl.editing) == (False, False)
        assert not self.dialogs.confirms
        # And back
        self.ctrl.set_writing(True)
        assert (self.view.editing, self.ctrl.editing) == (True, True)

    def test_leave_writing_with_text_asks(self):
        self.view.text = "Draft"
        self.dialogs.answer_confirm(False)
        self.ctrl.set_writing(False)
        # The draft stays and the view shows the writing again
        assert self.ctrl.editing and self.view.editing
        assert self.view.text == "Draft"
        text, title, ok, cancel = self.dialogs.confirms[0]
        assert text == tr("message.discard_text.text")
        assert (title, ok, cancel) == (tr("common.warning"), "Discard", "Keep")

    def test_leave_writing_and_discard(self):
        self.view.text = "Draft"
        self.ctrl.load_image(SAMPLE_IMG, datetime(2019, 1, 1))
        self.dialogs.answer_confirm(True)
        self.ctrl.set_writing(False)
        assert not self.ctrl.editing and not self.view.editing
        # Everything of the draft is gone
        assert self.view.text == "" and self.view.draft_image is None
        assert self.view.draft_date == NOW
        # The message mentions the image too
        assert self.dialogs.confirms[0][0] == tr("message.discard_text_image.text")
        assert not self.ctrl.can_undo  # It was confirmed

    def test_writing_clears_the_selection(self):
        self.read("Walk")
        self.ctrl.set_writing(True)
        assert self.ctrl.selected is None and self.view.selected is None

    def test_leaving_writing_shows_the_selected_entry_again(self):
        self.read("Spring")
        self.ctrl.set_writing(True)
        self.ctrl.select_entry(self.entry("Walk"))
        self.ctrl.set_writing(True)
        self.ctrl.set_writing(False)
        assert self.view.entry is None  # nothing is selected after writing


class TestSelecting(ControllerTestCase):
    def test_selecting_leaves_writing_and_shows_the_entry(self):
        walk = self.entry("Walk")
        self.ctrl.select_entry(walk)
        assert not self.ctrl.editing and not self.view.editing
        assert self.view.entry == walk and self.view.entry_image is None
        assert self.ctrl.selected == walk

    def test_photo_entry_shows_the_image(self):
        self.ctrl.select_entry(self.entry("Logo"))
        assert self.view.entry_image == os.path.join(img_dir, "IMG_1.jpg")

    def test_missing_image_is_not_shown(self):
        self.ctrl.select_entry(self.entry("Lost"))
        assert self.view.entry.text == "Lost photo" and self.view.entry_image is None

    def test_selecting_with_a_draft_asks(self):
        self.view.text = "Draft"
        self.dialogs.answer_confirm(False)
        self.ctrl.select_entry(self.entry("Walk"))
        assert self.ctrl.editing and self.view.text == "Draft"
        assert self.view.selected is None and self.view.entry is None

        self.dialogs.answer_confirm(True)
        self.ctrl.select_entry(self.entry("Walk"))
        assert not self.ctrl.editing and self.view.text == ""
        assert self.view.entry == self.entry("Walk")

    def test_selecting_while_reading_does_not_ask(self):
        self.read("Walk")
        self.read("Spring")
        assert self.view.entry.text == "Spring" and not self.dialogs.confirms

    def test_show_selected_image(self):
        self.ctrl.show_selected_image()  # nothing selected
        self.read("Walk")
        self.ctrl.show_selected_image()  # no image
        self.read("Lost")
        self.ctrl.show_selected_image()  # image file is missing
        assert self.dialogs.photos == []
        self.read("Logo")
        self.ctrl.show_selected_image()
        assert self.dialogs.photos == [os.path.join(img_dir, "IMG_1.jpg")]

    def test_adjacent_entries(self):
        ctrl, view = self.ctrl, self.view
        # Not while writing
        assert not ctrl.select_adjacent(1)

        ctrl.set_writing(False)
        # Nothing selected: the newest one is chosen, in both directions
        assert ctrl.select_adjacent(-1)
        assert view.entry.text.startswith("Walk") and view.selected == view.entry
        ctrl.selected = None
        assert ctrl.select_adjacent(1)
        assert view.entry.text.startswith("Walk")

        # Older and newer, without going past the ends
        assert not ctrl.select_adjacent(-1)
        for text in ["Logo", "Lost", "Spring"]:
            assert ctrl.select_adjacent(1)
            assert view.entry.text.startswith(text)
        assert not ctrl.select_adjacent(1)
        assert view.entry.text == "Spring"
        assert ctrl.select_adjacent(-1)
        assert view.entry.text == "Lost photo"

    def test_adjacent_entries_without_entries(self):
        self.ctrl.entries = []
        self.ctrl.set_writing(False)
        assert not self.ctrl.select_adjacent(1)


class TestSearch(ControllerTestCase):
    def test_search_filters_the_list(self):
        self.ctrl.set_query("sketch")
        assert self.texts() == ["Logo sketch"]
        assert self.view.total == 4
        self.ctrl.set_query("zzz")
        assert self.view.shown == [] and self.view.total == 4
        self.ctrl.set_query("")
        assert len(self.view.shown) == 4

    def test_selection_is_kept_if_still_shown(self):
        self.read("Logo")
        self.ctrl.set_query("sketch")
        assert self.view.selected == self.entry("Logo")
        self.ctrl.set_query("lake")
        # It is not in the list, but still shown on the page
        assert self.view.selected is None and self.ctrl.selected == self.entry("Logo")
        self.ctrl.set_query("")
        assert self.view.selected == self.entry("Logo")

    def test_adjacent_entries_are_the_found_ones(self):
        self.ctrl.set_writing(False)
        self.ctrl.set_query("o")  # Logo, Lost photo, Walk by the lake: not Spring
        assert len(self.ctrl.shown) == 3
        self.ctrl.select_adjacent(1)
        for _ in range(5):
            self.ctrl.select_adjacent(1)
        assert self.view.entry.text == "Lost photo"

    def test_reload_keeps_selection(self):
        self.read("Walk")
        self.ctrl.reload_entries()
        assert self.view.selected == self.entry("Walk")


class TestImage(ControllerTestCase):
    def test_load_image(self):
        # Only images
        assert not self.ctrl.load_image(os.path.join(DATA_DIR, "notes.txt"))
        assert self.ctrl.draft_image is None

        # The date is taken from the name of the file
        named = os.path.join(DATA_DIR, "IMG_20190304_101500.jpg")
        assert self.ctrl.load_image(named)
        assert self.view.draft_image == named
        assert self.view.draft_date == datetime(2019, 3, 4, 10, 15)

    def test_load_image_takes_the_modified_time_without_date_in_the_name(self):
        assert self.ctrl.load_image(SAMPLE_IMG)
        assert self.view.draft_date == datetime.fromtimestamp(
            os.path.getmtime(SAMPLE_IMG)
        ).replace(microsecond=0)

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        assert not self.ctrl.load_image(SAMPLE_IMG)
        assert self.ctrl.draft_image is None

    def test_show_draft_image(self):
        self.ctrl.show_draft_image()
        assert self.dialogs.photos == []
        self.ctrl.load_image(SAMPLE_IMG)
        self.ctrl.show_draft_image()
        assert self.dialogs.photos == [SAMPLE_IMG]

    def test_upload_image(self):
        assert not self.ctrl.upload_image()  # The user cancels
        assert self.dialogs.image_file_asked == 1 and self.ctrl.draft_image is None
        self.dialogs.image_file = SAMPLE_IMG
        assert self.ctrl.upload_image()
        assert self.view.draft_image == SAMPLE_IMG

    def test_upload_of_a_file_that_is_no_image(self):
        self.dialogs.image_file = os.path.join(DATA_DIR, "notes.txt")
        assert not self.ctrl.upload_image()
        assert self.dialogs.infos[0][0] == tr("message.no_image_file.text")
        assert self.ctrl.draft_image is None

    def test_upload_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.dialogs.image_file = SAMPLE_IMG
        assert not self.ctrl.upload_image()
        assert self.dialogs.image_file_asked == 0


class TestSelfie(ControllerTestCase):
    def test_selfie_is_loaded_with_the_time_of_taking_it(self):
        self.dialogs.selfie_source = SAMPLE_IMG
        self.ctrl.take_selfie()
        target = os.path.join(self.ctrl.temp.path, "IMG_20261023_120000_Self.png")
        assert self.dialogs.selfie_targets == [target]
        assert self.view.draft_image == target and os.path.isfile(target)
        assert self.view.draft_date == NOW

    def test_no_webcam(self):
        self.dialogs.no_webcam = True
        self.ctrl.take_selfie()
        assert self.dialogs.infos == [
            (tr("message.no_webcam.text"), tr("message.no_webcam.title"))
        ]
        assert self.ctrl.draft_image is None

    def test_cancelled(self):
        self.ctrl.take_selfie()
        assert self.ctrl.draft_image is None and not self.dialogs.infos

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.ctrl.take_selfie()
        assert self.dialogs.selfie_targets == []


class TestChangeDate(ControllerTestCase):
    def test_date_is_changed(self):
        self.dialogs.date = datetime(2021, 2, 3, 4, 5, 6)
        self.ctrl.change_date()
        assert self.dialogs.date_starts == [NOW]
        assert self.ctrl.draft_date == self.view.draft_date == self.dialogs.date

    def test_canceled(self):
        self.ctrl.change_date()
        assert self.ctrl.draft_date == NOW

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.dialogs.date = datetime(2021, 2, 3)
        self.ctrl.change_date()
        assert self.ctrl.draft_date == NOW and self.dialogs.date_starts == []


class TestChangeFolder(ControllerTestCase):
    def test_other_folder_is_loaded(self):
        with tempfile.TemporaryDirectory() as other:
            self.read("Walk")
            self.dialogs.folder = other
            self.ctrl.change_folder()
            assert self.view.folder == other
            assert self.ctrl.folder == DataFolder(other)
            assert os.path.isdir(os.path.join(other, "Img"))
            assert self.ctrl.entries == [] and self.view.total == 0
            assert self.ctrl.selected is None
            assert self.view.entry is None  # The page to read is empty
            # And the date starts again
            assert self.view.draft_date == NOW

    def test_other_folder_with_entries(self):
        with tempfile.TemporaryDirectory() as other:
            folder = DataFolder(other)
            folder.create()
            SqliteEntryStore(folder.db_file).save_entry(
                "Somewhere else", datetime(2019, 1, 1, 9)
            )
            self.dialogs.folder = other
            self.ctrl.change_folder()
            assert self.texts() == ["Somewhere else"]

    def test_no_folder_chosen(self):
        self.ctrl.change_folder()
        assert self.view.folder == DATA_DIR and self.view.total == 4


class TestSave(ControllerTestCase):
    def test_text_entry(self):
        self.now = datetime(2021, 5, 6, 7, 8, 9)
        self.ctrl.draft_date = datetime(2021, 1, 2, 3, 4, 5)
        self.view.text = "Brand new"
        assert self.ctrl.save()

        entries = STORE.load_all()
        assert entries[0].text == "Brand new" and entries[0].type == "text"
        assert entries[0].date_time == datetime(2021, 1, 2, 3, 4, 5)
        # The next entry starts
        assert self.view.text == "" and self.view.draft_date == self.now
        assert self.ctrl.editing and self.view.editing
        # And the list shows it
        assert self.texts()[0] == "Brand new" and self.view.total == 5

    def test_nothing_to_save(self):
        assert not self.ctrl.save()
        assert self.dialogs.infos == [
            (tr("message.no_text.text"), tr("message.no_text.title"))
        ]
        assert len(STORE.load_all()) == 4

    def test_photo_entry(self):
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "A photo"
        assert self.ctrl.save()

        entry = STORE.load_all()[0]
        assert (entry.type, entry.text) == ("photo", "A photo")
        assert entry.photo == "IMG_20210102_030405.jpg"
        assert os.path.isfile(os.path.join(img_dir, entry.photo))
        # The next entry starts without the image
        assert self.view.draft_image is None and self.ctrl.draft_image is None
        assert self.view.text == ""

    def test_image_with_same_date_can_be_added_again(self):
        for _ in range(2):
            self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
            self.view.text = "A photo"
            assert self.ctrl.save()
        # The dialog is asked with the folder of the images and the existing ones
        assert self.dialogs.image_choices == [(img_dir, ["IMG_20210102_030405.jpg"])]
        photos = {e.photo for e in STORE.load_all() if e.type == "photo"}
        assert {"IMG_20210102_030405.jpg", "IMG_20210102_030405_0.jpg"} <= photos

    def test_existing_image_can_be_used(self):
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "One"
        self.ctrl.save()
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "Two"
        self.dialogs.image_choice = 0
        assert self.ctrl.save()
        two = next(e for e in STORE.load_all() if e.text == "Two")
        assert two.photo == "IMG_20210102_030405.jpg"
        assert not os.path.exists(os.path.join(img_dir, "IMG_20210102_030405_0.jpg"))

    def test_no_decision_keeps_the_draft(self):
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "One"
        self.ctrl.save()

        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "Two"
        self.dialogs.image_choice = None
        assert not self.ctrl.save()
        assert self.view.text == "Two" and self.view.draft_image == SAMPLE_IMG
        assert not any(e.text == "Two" for e in STORE.load_all())
        assert NEW_IMAGE == -1  # The default choice of the fake dialogs

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.view.text = "Text"
        assert not self.ctrl.save()
        assert len(STORE.load_all()) == 4 and not self.dialogs.infos


class TestShortcuts(ControllerTestCase):
    def test_writing_shortcuts_only_work_while_writing(self):
        self.ctrl.set_writing(False)
        for action in ["save", "upload", "date", "selfie", "discard"]:
            self.ctrl.run_shortcut(action)
        assert self.dialogs.image_file_asked == 0
        assert self.dialogs.date_starts == [] and self.dialogs.selfie_targets == []
        assert not self.dialogs.infos

    def test_new_toggles_between_writing_and_reading(self):
        self.ctrl.run_shortcut("new")
        assert not self.ctrl.editing
        self.ctrl.run_shortcut("new")
        assert self.ctrl.editing

    def test_upload_asks_for_an_image(self):
        self.dialogs.image_file = SAMPLE_IMG
        self.ctrl.run_shortcut("upload")
        assert self.dialogs.image_file_asked == 1
        assert self.view.draft_image == SAMPLE_IMG

    def test_save_date_folder_selfie(self):
        self.ctrl.run_shortcut("save")
        assert len(self.dialogs.infos) == 1  # no text
        self.ctrl.run_shortcut("date")
        assert len(self.dialogs.date_starts) == 1
        self.ctrl.run_shortcut("folder")
        assert self.dialogs.folder_asked == 1
        self.ctrl.run_shortcut("selfie")
        assert len(self.dialogs.selfie_targets) == 1

    def test_prev_and_next(self):
        self.ctrl.run_shortcut("new")
        self.ctrl.run_shortcut("prev")
        assert self.view.entry.text.startswith("Walk")
        self.ctrl.run_shortcut("prev")
        assert self.view.entry.text == "Logo sketch"
        self.ctrl.run_shortcut("next")
        assert self.view.entry.text.startswith("Walk")

    def test_quit(self):
        self.ctrl.run_shortcut("quit")
        assert self.view.closed


class TestDiscard(ControllerTestCase):
    def draft(self):
        self.view.text = "Draft"
        self.ctrl.load_image(SAMPLE_IMG, datetime(2019, 1, 1))

    def test_nothing_to_discard(self):
        assert not self.ctrl.discard_draft()
        assert not self.ctrl.can_undo and self.view.undo is None
        # A date alone is not worth keeping
        self.ctrl.draft_date = datetime(2020, 1, 1)
        assert not self.ctrl.discard_draft()

    def test_discard_clears_text_image_and_date(self):
        self.draft()
        assert self.ctrl.discard_draft()
        assert self.view.text == "" and self.view.draft_image is None
        assert self.ctrl.draft_image is None and self.view.draft_date == NOW
        assert self.view.undo == tr("undo.draft_discarded")
        assert not self.dialogs.confirms

    def test_undo_and_redo(self):
        self.draft()
        self.ctrl.discard_draft()
        assert self.ctrl.can_undo and not self.ctrl.can_redo
        assert self.ctrl.undo()
        assert self.view.text == "Draft" and self.view.draft_image == SAMPLE_IMG
        assert self.ctrl.draft_image == SAMPLE_IMG
        assert self.view.draft_date == datetime(2019, 1, 1)
        assert self.view.undo is None and self.view.redo == tr("undo.draft_discarded")
        assert not self.ctrl.undo()  # only once

        assert self.ctrl.redo()
        assert self.view.text == "" and self.view.draft_image is None
        assert self.view.undo == tr("undo.draft_discarded") and self.view.redo is None
        assert not self.ctrl.redo()

    def test_undo_text_only(self):
        self.view.text = "Draft"
        self.ctrl.discard_draft()
        self.ctrl.undo()
        assert self.view.text == "Draft" and self.view.draft_image is None

    def test_editing_the_draft_ends_the_undo(self):
        self.draft()
        self.ctrl.discard_draft()
        self.view.text = "Something new"
        self.ctrl.draft_edited()
        assert not self.ctrl.can_undo and self.view.undo is None
        assert not self.ctrl.undo()
        assert self.view.text == "Something new"

    def test_other_changes_end_the_undo(self):
        for change in (
            lambda: self.ctrl.load_image(SAMPLE_IMG),
            lambda: setattr(self.dialogs, "date", datetime(2020, 5, 5))
            or self.ctrl.change_date(),
            lambda: self.ctrl.set_writing(True),
        ):
            self.draft()
            self.ctrl.discard_draft()
            change()
            assert not self.ctrl.can_undo and self.view.undo is None
            self.ctrl.draft_image = None
            self.view.text = ""

    def test_saving_ends_the_undo(self):
        self.view.text = "Draft"
        self.ctrl.discard_draft()
        self.view.text = "Something else"
        assert self.ctrl.save()
        assert not self.ctrl.can_undo and self.view.undo is None

    def test_a_new_change_ends_the_redo(self):
        self.view.text = "Draft"
        self.ctrl.discard_draft()
        self.ctrl.undo()
        assert self.ctrl.can_redo
        self.ctrl.discard_draft()
        assert not self.ctrl.can_redo and self.view.redo is None

    def test_shortcut(self):
        self.view.text = "Draft"
        self.ctrl.run_shortcut("discard")
        assert self.view.text == "" and self.ctrl.can_undo
        self.ctrl.set_writing(False)
        self.view.text = "Not part of an entry that is read"
        self.ctrl.run_shortcut("discard")
        assert self.view.text == "Not part of an entry that is read"

    def test_remove_image_keeps_the_text(self):
        self.draft()
        assert self.ctrl.remove_image()
        assert self.view.draft_image is None and self.view.text == "Draft"
        assert self.view.draft_date == NOW
        assert self.view.undo == tr("undo.image_removed")
        self.view.text = "Changed text"  # not through the text field
        assert self.ctrl.undo()
        assert self.view.draft_image == SAMPLE_IMG
        assert self.view.draft_date == datetime(2019, 1, 1)
        assert self.view.text == "Changed text"
        assert self.ctrl.redo()
        assert self.view.draft_image is None

    def test_remove_image_without_image(self):
        assert not self.ctrl.remove_image()
        assert self.view.undo is None

    def test_history_is_limited(self):
        for n in range(MAX_HISTORY + 5):
            self.view.text = f"Draft {n}"
            self.ctrl.discard_draft()
        undone = 0
        while self.ctrl.undo():
            undone += 1
        assert undone == MAX_HISTORY

    def test_undo_after_leaving_writing_does_nothing(self):
        self.view.text = "Draft"
        self.ctrl.discard_draft()
        self.ctrl.set_writing(False)
        assert not self.ctrl.can_undo


class TestEditing(ControllerTestCase):
    def test_edit_shows_the_entry_in_the_writing_page(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        view = self.view
        assert self.ctrl.editing and self.ctrl.editing_entry == self.entry("Walk")
        assert view.editing and view.editing_existing
        assert view.text == "Walk by the lake\n\nsecond line"
        assert view.draft_date == datetime(2020, 10, 22, 21, 32)
        assert view.draft_image is None
        # The entry stays selected
        assert self.ctrl.selected == self.entry("Walk")

    def test_edit_photo_entry(self):
        self.read("Logo")
        self.ctrl.edit_selected()
        image = os.path.join(img_dir, "IMG_1.jpg")
        assert self.view.draft_image == image
        assert self.ctrl.draft_image == image

    def test_nothing_to_edit(self):
        self.ctrl.edit_selected()  # writing
        assert self.ctrl.editing_entry is None and not self.view.editing_existing
        self.ctrl.set_writing(False)
        self.ctrl.edit_selected()  # nothing selected
        assert not self.ctrl.editing

    def test_save_changes_the_entry(self):
        self.read("Walk")
        walk_id = self.entry("Walk").id
        self.ctrl.edit_selected()
        self.view.text = "Changed text"
        self.dialogs.date = datetime(2020, 11, 1, 9)
        self.ctrl.change_date()
        assert self.ctrl.save()

        # Back to reading it, in the new place of the list
        assert not self.ctrl.editing and not self.view.editing
        assert self.ctrl.editing_entry is None and not self.view.editing_existing
        assert self.view.text == "" and self.view.draft_date == NOW
        assert self.view.entry.text == "Changed text"
        assert self.view.entry.id == walk_id
        assert self.view.selected.id == walk_id
        assert self.texts()[0] == "Changed text" and len(self.view.shown) == 4
        assert next(e.text for e in STORE.load_all()) == "Changed text"

    def test_save_without_text_is_refused(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        self.view.text = ""
        assert not self.ctrl.save()
        assert self.ctrl.editing_entry is not None
        assert self.dialogs.infos[0][0] == tr("message.no_text.text")

    def test_add_an_image_to_a_text_entry(self):
        self.read("Spring")
        self.ctrl.edit_selected()
        self.ctrl.load_image(SAMPLE_IMG, datetime(2020, 3, 3, 7, 30))
        assert self.ctrl.save()
        entry = self.view.entry
        assert entry.type == "photo" and entry.photo is not None
        assert self.view.entry_image == os.path.join(img_dir, entry.photo)
        assert os.path.isfile(self.view.entry_image)

    def test_the_same_image_is_not_copied_again(self):
        self.read("Logo")
        before = sorted(os.listdir(img_dir))
        self.ctrl.edit_selected()
        self.view.text = "Logo sketch, better"
        assert self.ctrl.save()
        assert self.view.entry.photo == "IMG_1.jpg"
        assert sorted(os.listdir(img_dir)) == before
        assert not self.dialogs.image_choices

    def test_replace_the_image(self):
        self.read("Logo")
        self.ctrl.edit_selected()
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 2, 3, 4, 5, 6))
        assert self.ctrl.save()
        entry = self.view.entry
        assert entry.photo != "IMG_1.jpg" and entry.date_time.year == 2021
        assert os.path.isfile(os.path.join(img_dir, entry.photo))
        # The old image is not deleted
        assert os.path.isfile(os.path.join(img_dir, "IMG_1.jpg"))

    def test_remove_the_image_makes_a_text_entry(self):
        self.read("Logo")
        self.ctrl.edit_selected()
        self.ctrl.remove_image()
        assert self.ctrl.save()
        assert self.view.entry.type == "text" and self.view.entry.photo is None
        assert self.view.entry_image is None

    def test_an_entry_with_a_missing_image_keeps_its_photo(self):
        self.read("Lost")  # The image file is missing
        self.ctrl.edit_selected()
        assert self.view.draft_image is None
        self.view.text = "Lost photo, still lost"
        assert self.ctrl.save()
        assert self.view.entry.type == "photo"
        assert self.view.entry.photo == "missing.jpg"

    def test_cancel_without_changes(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        assert self.ctrl.cancel_edit()
        assert not self.dialogs.confirms and not self.ctrl.editing
        assert self.view.entry == self.entry("Walk") and self.view.text == ""
        assert not self.view.editing_existing

    def test_cancel_with_changes_asks(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        self.view.text = "Changed"
        self.dialogs.answer_confirm(False, True)
        assert not self.ctrl.cancel_edit()
        assert self.ctrl.editing and self.view.text == "Changed"
        assert self.dialogs.confirms[0][0] == tr("message.discard_changes.text")
        assert self.ctrl.cancel_edit()
        assert not self.ctrl.editing and self.view.entry.text.startswith("Walk")
        assert self.entry("Walk").text.startswith("Walk")  # not changed

    def test_discard_cancels_the_edit(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        assert self.ctrl.discard_draft()
        assert not self.ctrl.editing and not self.view.undo

    def test_leaving_to_other_pages_asks_about_changes(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        self.view.text = "Changed"
        self.dialogs.answer_confirm(False, False, False, True)
        self.ctrl.select_entry(self.entry("Spring"))  # keep editing
        assert self.ctrl.editing and self.view.selected == self.entry("Walk")
        self.ctrl.set_writing(False)
        assert self.ctrl.editing and self.view.editing
        self.ctrl.set_writing(True)
        assert self.ctrl.editing_entry is not None and self.view.editing_existing
        # Now throw the changes away and go to the other entry
        self.ctrl.select_entry(self.entry("Spring"))
        assert not self.ctrl.editing and self.view.entry == self.entry("Spring")
        assert self.dialogs.confirm_answers == deque()

    def test_new_entry_while_changing(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        self.ctrl.set_writing(True)  # nothing changed, so no question
        assert self.ctrl.editing and self.ctrl.editing_entry is None
        assert not self.view.editing_existing and self.view.text == ""
        assert self.ctrl.selected is None

    def test_unchanged_edit_can_be_closed(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        assert self.ctrl.request_close() and not self.dialogs.confirms
        self.view.text = "x"
        self.dialogs.answer_confirm(False)
        assert not self.ctrl.request_close()

    def test_change_folder_stops_editing(self):
        self.read("Walk")
        self.ctrl.edit_selected()
        with tempfile.TemporaryDirectory() as other:
            self.dialogs.folder = other
            self.ctrl.change_folder()
        assert not self.ctrl.editing and self.ctrl.editing_entry is None
        assert not self.view.editing_existing

    def test_shortcut(self):
        self.ctrl.set_writing(False)
        self.ctrl.run_shortcut("edit")  # nothing selected
        assert not self.ctrl.editing
        self.read("Walk")
        self.ctrl.run_shortcut("edit")
        assert self.ctrl.editing_entry is not None


class TestDeleting(ControllerTestCase):
    def test_delete_moves_to_the_trash(self):
        self.read("Spring")
        assert self.ctrl.delete_selected()
        assert "Spring" not in self.texts() and self.view.total == 4
        assert self.texts(self.view.trash) == ["Spring"]
        assert self.view.trash[0].deleted_at == NOW
        assert self.ctrl.selected is None and self.view.entry is None
        assert self.view.undo == tr("undo.entry_deleted")
        assert not self.dialogs.confirms
        assert [e.text for e in STORE.load_trash()] == ["Spring"]

    def test_undo_and_redo(self):
        self.read("Spring")
        self.ctrl.delete_selected()
        assert self.ctrl.undo()
        assert "Spring" in self.texts() and self.view.trash == []
        assert self.view.entry.text == "Spring" and self.view.selected.text == "Spring"
        assert self.view.undo is None and self.view.redo == tr("undo.entry_deleted")

        assert self.ctrl.redo()
        assert "Spring" not in self.texts() and len(self.view.trash) == 1
        assert self.view.entry is None
        assert self.view.undo == tr("undo.entry_deleted") and self.view.redo is None

    def test_undo_does_not_leave_the_writing_page(self):
        self.read("Spring")
        self.ctrl.delete_selected()
        self.ctrl.set_writing(True)
        self.view.text = "Draft"
        self.ctrl.draft_edited()
        assert self.ctrl.can_undo  # Writing does not end it
        assert self.ctrl.undo()
        assert self.ctrl.editing and self.view.text == "Draft"
        assert "Spring" in self.texts() and self.view.entry is None

    def test_nothing_to_delete(self):
        assert not self.ctrl.delete_selected()  # writing
        self.ctrl.set_writing(False)
        assert not self.ctrl.delete_selected()  # nothing selected
        assert self.view.trash == [] and not self.ctrl.can_undo

    def test_the_image_stays_with_the_entry_in_the_trash(self):
        self.read("Logo")
        self.ctrl.delete_selected()
        assert os.path.isfile(os.path.join(img_dir, "IMG_1.jpg"))
        self.ctrl.select_entry(self.ctrl.trash[0])
        assert self.view.entry_image == os.path.join(img_dir, "IMG_1.jpg")

    def test_change_folder_ends_the_history(self):
        self.read("Spring")
        self.ctrl.delete_selected()
        self.ctrl.undo()
        with tempfile.TemporaryDirectory() as other:
            self.dialogs.folder = other
            self.ctrl.change_folder()
        assert not self.ctrl.can_undo and not self.ctrl.can_redo
        assert self.view.undo is None and self.view.redo is None

    def test_delete_is_undone_in_order(self):
        for text in ("Spring", "Walk"):
            self.read(text)
            self.ctrl.delete_selected()
        assert self.texts() == ["Logo sketch", "Lost photo"]
        self.ctrl.undo()
        assert self.texts()[0] == "Walk by the lake"
        self.ctrl.undo()
        assert len(self.view.shown) == 4 and self.view.trash == []


class TestTrash(ControllerTestCase):
    def delete(self, *texts):
        for text in texts:
            self.read(text)
            self.ctrl.delete_selected()

    def read_trashed(self, text):
        self.ctrl.select_entry(next(e for e in self.ctrl.trash if text in e.text))

    def test_the_trash_is_listed_below_the_entries(self):
        self.delete("Spring", "Walk")
        # The last deleted first
        assert self.texts(self.view.trash) == ["Walk by the lake", "Spring"]
        assert self.texts() == ["Logo sketch", "Lost photo"]
        assert self.view.total == 4

    def test_selecting_an_entry_in_the_trash(self):
        self.delete("Spring")
        self.read_trashed("Spring")
        assert self.view.entry.text == "Spring"
        assert self.view.entry.deleted_at == NOW

    def test_search_includes_the_trash(self):
        self.delete("Spring", "Walk")
        self.ctrl.set_query("spring")
        assert self.texts() == [] and self.texts(self.view.trash) == ["Spring"]
        assert self.view.total == 4
        self.ctrl.set_query("")
        assert len(self.view.trash) == 2

    def test_adjacent_entries_go_on_into_the_trash(self):
        self.delete("Walk")
        self.ctrl.set_writing(False)
        for _ in range(3):
            self.ctrl.select_adjacent(1)
        assert self.view.entry.text == "Spring"
        assert self.ctrl.select_adjacent(1)
        assert self.view.entry.text.startswith("Walk")
        assert self.view.entry.deleted_at is not None

    def test_restore(self):
        self.delete("Spring")
        self.read_trashed("Spring")
        assert self.ctrl.restore_selected()
        assert self.view.trash == [] and "Spring" in self.texts()
        assert self.view.entry is None
        assert self.view.undo == tr("undo.entry_restored")

    def test_restore_can_be_undone(self):
        self.delete("Spring")
        self.read_trashed("Spring")
        self.ctrl.restore_selected()
        assert self.ctrl.undo()
        assert self.texts(self.view.trash) == ["Spring"]
        assert "Spring" not in self.texts()
        assert self.ctrl.redo()
        assert "Spring" in self.texts()

    def test_restore_only_in_the_trash(self):
        self.read("Walk")
        assert not self.ctrl.restore_selected()
        assert not self.ctrl.delete_selected_forever()

    def test_delete_forever_asks(self):
        self.delete("Spring")
        self.read_trashed("Spring")
        self.dialogs.answer_confirm(False, True)
        assert not self.ctrl.delete_selected_forever()
        assert len(self.ctrl.trash) == 1
        assert self.ctrl.delete_selected_forever()
        assert self.ctrl.trash == [] and STORE.load_trash() == []
        assert self.dialogs.confirms[0][0] == tr("message.delete_forever.text")
        assert self.view.entry is None and self.view.trash == []
        # It can not be undone
        assert not self.ctrl.can_undo

    def test_delete_forever_removes_the_image(self):
        self.delete("Logo")
        path = os.path.join(img_dir, "IMG_1.jpg")
        self.read_trashed("Logo")
        self.dialogs.answer_confirm(True)
        self.ctrl.delete_selected_forever()
        assert not os.path.exists(path)

    def test_an_image_used_by_another_entry_is_kept(self):
        STORE.save_entry(
            "Same image", datetime(2020, 10, 20, 18, 15), "photo", "IMG_1.jpg"
        )
        self.ctrl.reload_entries()
        self.delete("Logo")
        self.read_trashed("Logo")
        self.dialogs.answer_confirm(True)
        self.ctrl.delete_selected_forever()
        assert os.path.exists(os.path.join(img_dir, "IMG_1.jpg"))

    def test_a_missing_image_is_no_problem(self):
        self.delete("Lost")
        self.read_trashed("Lost")
        self.dialogs.answer_confirm(True)
        assert self.ctrl.delete_selected_forever()

    def test_empty_trash(self):
        assert not self.ctrl.empty_trash()  # nothing in it
        self.delete("Spring", "Logo")
        self.dialogs.answer_confirm(False, True)
        assert not self.ctrl.empty_trash()
        assert len(self.ctrl.trash) == 2
        assert self.ctrl.empty_trash()
        assert self.ctrl.trash == [] and self.view.trash == []
        assert not os.path.exists(os.path.join(img_dir, "IMG_1.jpg"))
        assert self.dialogs.confirms[0][0] == tr("message.empty_trash.text", count=2)
        assert self.view.total == 2  # the entries are not touched
        assert not self.ctrl.can_undo

    def test_no_editing_in_the_trash(self):
        self.delete("Spring")
        self.ctrl.set_writing(False)
        self.read_trashed("Spring")
        self.ctrl.edit_selected()
        assert not self.ctrl.editing
        assert not self.ctrl.delete_selected()

    def test_the_trash_stays_after_a_restart(self):
        self.delete("Spring")
        other = DiaryController(FakeView(), FakeDialogs(), now=lambda: NOW)
        assert other.start()
        assert [e.text for e in other.trash] == ["Spring"]
        other.temp.remove()


class TestClosing(ControllerTestCase):
    def test_close_without_draft(self):
        assert self.ctrl.request_close()
        assert not self.dialogs.confirms

    def test_close_with_text_asks(self):
        self.view.text = "Draft"
        self.dialogs.answer_confirm(False, True)
        assert not self.ctrl.request_close()
        assert self.ctrl.request_close()
        assert len(self.dialogs.confirms) == 2

    def test_close_with_image_asks(self):
        self.ctrl.load_image(SAMPLE_IMG)
        self.dialogs.answer_confirm(True)
        assert self.ctrl.request_close()
        assert self.dialogs.confirms[0][0] == tr("message.discard_text_image.text")

    def test_close_while_reading(self):
        self.ctrl.set_writing(False)
        self.view.text = "Not part of an entry that is read"
        assert self.ctrl.request_close()

    def test_finish_cleans_up(self):
        temp = self.ctrl.temp.path
        self.ctrl.finish()
        assert not os.path.exists(temp)
        assert settings.get_data_dir() == DATA_DIR


class TestEmptyDiary(ControllerTestCase):
    seed = False

    def test_nothing_to_show(self):
        assert self.view.total == 0 and self.view.shown == []
        self.ctrl.set_writing(False)
        assert self.view.entry is None
        assert not self.ctrl.select_adjacent(1)

    def test_first_entry(self):
        self.view.text = "First"
        assert self.ctrl.save()
        assert self.texts() == ["First"] and self.view.total == 1
