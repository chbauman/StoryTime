import os
import shutil
import tempfile
from contextlib import ExitStack
from datetime import datetime
from unittest import TestCase

from story_time import settings
from story_time.controller import DiaryController
from story_time.folders import DataFolder
from story_time.images import NEW_IMAGE
from story_time.texts import tr
from story_time.xml_storage import EntryStore
from tests.fakes import FakeDialogs, FakeView
from tests.helpers import (
    DATA_DIR,
    SAMPLE_IMG_DIR,
    create_test_dirs,
    img_dir,
    use_data_dir,
    xml_dir,
)

SAMPLE_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")
NOW = datetime(2026, 10, 23, 12, 0, 0)
STORE = EntryStore(xml_dir)


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
        assert (view.editing, view.photo_mode) == (True, False)
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
            assert os.path.isdir(os.path.join(folder, "XML"))
            assert self.view.total == 0

    def test_no_folder_chosen_does_not_start(self):
        assert not self.ctrl.start()
        assert self.view.folder is None
        assert not os.path.exists("XML") and not os.path.exists("Img")


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
        self.ctrl.set_photo_mode(True)
        self.ctrl.load_image(SAMPLE_IMG, datetime(2019, 1, 1))
        self.dialogs.answer_confirm(True)
        self.ctrl.set_writing(False)
        assert not self.ctrl.editing and not self.view.editing
        # Everything of the draft is gone
        assert self.view.text == "" and self.view.draft_image is None
        assert (self.ctrl.photo_mode, self.view.photo_mode) == (False, False)
        assert self.view.draft_date == NOW
        # The message mentions the image too
        assert self.dialogs.confirms[0][0] == tr("message.discard_text_image.text")

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


class TestPhotoMode(ControllerTestCase):
    def test_photo_mode_on_and_off_keeps_text_and_date(self):
        self.view.text = "Kept text"
        self.ctrl.draft_date = datetime(2020, 1, 1)
        self.ctrl.set_photo_mode(True)
        assert self.ctrl.photo_mode and self.view.photo_mode
        self.ctrl.set_photo_mode(False)
        assert not self.ctrl.photo_mode and not self.view.photo_mode
        assert self.view.text == "Kept text"
        assert self.ctrl.draft_date == datetime(2020, 1, 1)
        assert not self.dialogs.confirms

    def test_leaving_photo_mode_with_image_asks(self):
        self.view.text = "Kept text"
        self.ctrl.set_photo_mode(True)
        self.ctrl.load_image(SAMPLE_IMG, datetime(2019, 5, 6, 7, 8))
        assert self.view.draft_date == datetime(2019, 5, 6, 7, 8)

        # Keeping the image
        self.dialogs.answer_confirm(False)
        self.ctrl.set_photo_mode(False)
        assert self.ctrl.photo_mode and self.view.photo_mode
        assert self.view.draft_image == SAMPLE_IMG
        assert self.dialogs.confirms[0][0] == tr("message.discard_image.text")

        # Discarding it keeps the text, but the date is not the one of the image
        self.dialogs.answer_confirm(True)
        self.ctrl.set_photo_mode(False)
        assert not self.ctrl.photo_mode and not self.view.photo_mode
        assert self.view.draft_image is None and self.ctrl.draft_image is None
        assert self.view.text == "Kept text"
        assert self.view.draft_date == NOW

    def test_text_alone_is_not_asked_about(self):
        self.ctrl.set_photo_mode(True)
        self.view.text = "Only text"
        self.ctrl.set_photo_mode(False)
        assert not self.dialogs.confirms

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.ctrl.set_photo_mode(True)
        assert not self.ctrl.photo_mode and not self.view.photo_mode

    def test_load_image(self):
        # Only in the photo mode
        assert not self.ctrl.load_image(SAMPLE_IMG)
        assert self.ctrl.draft_image is None
        self.ctrl.set_photo_mode(True)

        # Only images
        assert not self.ctrl.load_image(os.path.join(DATA_DIR, "notes.txt"))

        # The date is taken from the name of the file
        named = os.path.join(DATA_DIR, "IMG_20190304_101500.jpg")
        assert self.ctrl.load_image(named)
        assert self.view.draft_image == named
        assert self.view.draft_date == datetime(2019, 3, 4, 10, 15)

    def test_load_image_takes_the_modified_time_without_date_in_the_name(self):
        self.ctrl.set_photo_mode(True)
        assert self.ctrl.load_image(SAMPLE_IMG)
        assert self.view.draft_date == datetime.fromtimestamp(
            os.path.getmtime(SAMPLE_IMG)
        ).replace(microsecond=0)

    def test_show_draft_image(self):
        self.ctrl.show_draft_image()
        assert self.dialogs.photos == []
        self.ctrl.set_photo_mode(True)
        self.ctrl.load_image(SAMPLE_IMG)
        self.ctrl.show_draft_image()
        assert self.dialogs.photos == [SAMPLE_IMG]


class TestSelfie(ControllerTestCase):
    def test_selfie_is_loaded_with_the_time_of_taking_it(self):
        self.dialogs.selfie_source = SAMPLE_IMG
        self.ctrl.take_selfie()
        target = os.path.join(self.ctrl.temp.path, "IMG_20261023_120000_Self.png")
        assert self.dialogs.selfie_targets == [target]
        assert (self.ctrl.photo_mode, self.view.photo_mode) == (True, True)
        assert self.view.draft_image == target and os.path.isfile(target)
        assert self.view.draft_date == NOW

    def test_no_webcam(self):
        self.dialogs.no_webcam = True
        self.ctrl.take_selfie()
        assert self.dialogs.infos == [
            (tr("message.no_webcam.text"), tr("message.no_webcam.title"))
        ]
        assert self.ctrl.draft_image is None
        # The photo mode was entered anyway, nothing is lost by it
        assert self.ctrl.photo_mode

    def test_cancelled(self):
        self.ctrl.take_selfie()
        assert self.ctrl.draft_image is None and not self.dialogs.infos

    def test_not_while_reading(self):
        self.ctrl.set_writing(False)
        self.ctrl.take_selfie()
        assert self.dialogs.selfie_targets == []

    def test_selfie_when_already_in_photo_mode_does_not_ask(self):
        self.ctrl.set_photo_mode(True)
        self.ctrl.take_selfie()
        assert not self.dialogs.confirms


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
            assert os.path.isdir(os.path.join(other, "XML"))
            assert self.ctrl.entries == [] and self.view.total == 0
            assert self.ctrl.selected is None
            assert self.view.entry is None  # The page to read is empty
            # And the date starts again
            assert self.view.draft_date == NOW

    def test_other_folder_with_entries(self):
        with tempfile.TemporaryDirectory() as other:
            folder = DataFolder(other)
            folder.create()
            EntryStore(folder.xml_folder).save_entry(
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
        # The next entry starts, in the same mode
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

    def test_photo_without_image(self):
        self.ctrl.set_photo_mode(True)
        self.view.text = "Text"
        assert not self.ctrl.save()
        assert self.dialogs.infos == [
            (tr("message.no_image.text"), tr("message.no_image.title"))
        ]
        assert self.view.text == "Text"

    def test_photo_entry(self):
        self.ctrl.set_photo_mode(True)
        self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
        self.view.text = "A photo"
        assert self.ctrl.save()

        entry = STORE.load_all()[0]
        assert (entry.type, entry.text) == ("photo", "A photo")
        assert entry.photo == "IMG_20210102_030405.jpg"
        assert os.path.isfile(os.path.join(img_dir, entry.photo))
        # The next entry starts in the photo mode, without the image
        assert self.view.photo_mode and self.view.draft_image is None
        assert self.view.text == ""

    def test_image_with_same_date_can_be_added_again(self):
        self.ctrl.set_photo_mode(True)
        for _ in range(2):
            self.ctrl.load_image(SAMPLE_IMG, datetime(2021, 1, 2, 3, 4, 5))
            self.view.text = "A photo"
            assert self.ctrl.save()
        # The dialog is asked with the folder of the images and the existing ones
        assert self.dialogs.image_choices == [(img_dir, ["IMG_20210102_030405.jpg"])]
        photos = {e.photo for e in STORE.load_all() if e.type == "photo"}
        assert {"IMG_20210102_030405.jpg", "IMG_20210102_030405_0.jpg"} <= photos

    def test_existing_image_can_be_used(self):
        self.ctrl.set_photo_mode(True)
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
        self.ctrl.set_photo_mode(True)
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
        for action in ["save", "photo", "date", "selfie"]:
            self.ctrl.run_shortcut(action)
        assert not self.ctrl.photo_mode
        assert self.dialogs.date_starts == [] and self.dialogs.selfie_targets == []
        assert not self.dialogs.infos

    def test_new_toggles_between_writing_and_reading(self):
        self.ctrl.run_shortcut("new")
        assert not self.ctrl.editing
        self.ctrl.run_shortcut("new")
        assert self.ctrl.editing

    def test_photo_toggles_the_mode(self):
        self.ctrl.run_shortcut("photo")
        assert self.ctrl.photo_mode
        self.ctrl.run_shortcut("photo")
        assert not self.ctrl.photo_mode

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
        self.ctrl.set_photo_mode(True)
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
