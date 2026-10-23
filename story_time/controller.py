"""The logic of the main window, without any GUI.

The `DiaryController` knows what the user can do and what happens then: writing
and reading entries, the draft with its image and date, the photo mode, the
list with the search, and saving. It does not know about widgets. Everything it
shows goes through a `View` and all questions to the user are asked through
`Dialogs`. The real ones are in `user_interface.py` and `dialogs.py`, the tests
use fake ones.
"""

import os
from datetime import datetime
from typing import Callable, Optional, Protocol

from story_time.dates import date_of_image_file, img_name_from_time
from story_time.folders import DataFolder, TempFolder, get_data_folder, save_data_folder
from story_time.images import copy_img_file_to_imgs, is_supported_image
from story_time.texts import tr
from story_time.xml_storage import Entry, EntryStore, filter_entries


class NoWebcamError(RuntimeError):
    """Raised if no frame can be read from the webcam."""


class Dialogs(Protocol):
    """The questions to the user and the dialogs the controller needs."""

    def ask_folder(self) -> Optional[str]:
        """Asks for the folder with the data, `None` if there is none chosen."""

    def confirm(self, text: str, title: str, ok_label: str, cancel_label: str) -> bool:
        """Asks a question, returns whether the user chose the OK label."""

    def info(self, text: str, title: str) -> None:
        """Shows a message."""

    def choose_image(self, img_folder: str, files: list[str]) -> Optional[int]:
        """Asks which one of the images with the same date to use for the entry.

        The images are the files with the given names in the image folder.

        Returns the index of the chosen image, `images.NEW_IMAGE` to add the new
        image anyway and `None` if there is no decision.
        """

    def pick_date(self, start: datetime) -> Optional[datetime]:
        """Lets the user pick a date and time, `None` if the user cancels."""

    def take_selfie(self, save_to: str) -> bool:
        """Takes a picture with the webcam and saves it as `save_to`.

        Returns whether a picture was taken. Raises `NoWebcamError` if there
        is no webcam.
        """

    def show_photo(self, path: str) -> None:
        """Shows the image in large."""


class View(Protocol):
    """What the controller needs of the window to show things."""

    def get_text(self) -> str:
        """The text in the text input."""

    def set_text(self, text: str) -> None:
        """Sets the text in the text input."""

    def show_mode(self, editing: bool, photo_mode: bool) -> None:
        """Shows the page to write or to read, and whether to add an image."""

    def show_draft_image(self, path: Optional[str]) -> None:
        """Shows the image of the entry that is written, none if `path` is None."""

    def show_draft_date(self, date_time: datetime) -> None:
        """Shows the date of the entry that is written."""

    def show_entry(self, entry: Optional[Entry], image: Optional[str]) -> None:
        """Shows an entry with its image, nothing if the entry is None."""

    def show_entries(
        self, shown: list[Entry], total: int, selected: Optional[Entry]
    ) -> None:
        """Shows the list of entries, with the selected one if it is in it.

        `total` is the number of all entries, also the ones not shown.
        """

    def select_entry(self, entry: Optional[Entry]) -> None:
        """Selects an entry in the list, deselects if it is None."""

    def show_folder(self, path: str) -> None:
        """Shows the folder with the data."""

    def close(self) -> None:
        """Closes the window."""


#: The actions of the shortcuts that only make sense while writing.
WRITING_ONLY = {"save", "photo", "date", "selfie"}


class DiaryController:
    """The logic of the main window."""

    def __init__(
        self,
        view: View,
        dialogs: Dialogs,
        now: Callable[[], datetime] = lambda: datetime.now().replace(microsecond=0),
    ) -> None:
        """
        Args:
            view: Shows everything.
            dialogs: Asks the user.
            now: Gives the current time. Can be replaced in tests.
        """
        self.view = view
        self.dialogs = dialogs
        self._now = now

        #: Whether a new entry is written, otherwise the entries are read.
        self.editing = True
        #: Whether the entry that is written gets an image.
        self.photo_mode = False
        #: The image of the entry that is written, if one is loaded.
        self.draft_image: Optional[str] = None
        #: The date of the entry that is written.
        self.draft_date = now()

        self._folder: Optional[DataFolder] = None
        self._store: Optional[EntryStore] = None
        #: The folder for the pictures taken with the webcam until they are saved.
        self.temp = TempFolder()

        self.entries: list[Entry] = []
        self.query = ""
        #: The entry that is shown on the page to read.
        self.selected: Optional[Entry] = None

    # ----------------------------------------------------------------- start / end

    @property
    def folder(self) -> DataFolder:
        """The folder with the data, which is there after `start`."""
        assert self._folder is not None, "The controller was not started."
        return self._folder

    @property
    def store(self) -> EntryStore:
        """The entries in the data folder, which are there after `start`."""
        assert self._store is not None, "The controller was not started."
        return self._store

    def start(self) -> bool:
        """Gets the data folder and shows everything.

        Returns False if there is no data folder, as the app cannot run then.
        """
        folder = get_data_folder(self.dialogs.ask_folder)
        if folder is None:
            return False
        self._use_folder(folder)
        self.reload_entries()
        self._show_all()
        return True

    def request_close(self) -> bool:
        """Asks if there is something unsaved. Returns whether to close."""
        return self._check_discard() is not None

    def finish(self) -> None:
        """To be called when the app is closed."""
        if self._folder is not None:
            save_data_folder(self._folder)
        self.temp.remove()

    # --------------------------------------------------------------- entries / list

    @property
    def shown(self) -> list[Entry]:
        """The entries matching the search, newest first."""
        return filter_entries(self.entries, self.query)

    def reload_entries(self) -> None:
        """Loads all entries and shows them in the list."""
        self.entries = self.store.load_all()
        if self.selected not in self.entries:
            self.selected = None
        self._show_entries()

    def set_query(self, query: str) -> None:
        """Searches the entries."""
        self.query = query
        self._show_entries()

    def select_entry(self, entry: Entry) -> None:
        """The user selected an entry in the list, to read it."""
        if self.editing:
            discard = self._check_discard()
            if discard is None:
                # Keep writing, so nothing is selected
                self.view.select_entry(None)
                return
            self._reset_draft()
            self.editing = False
        self.selected = entry
        self.view.show_mode(self.editing, self.photo_mode)
        self.view.show_entry(entry, self._image_of(entry))

    def select_adjacent(self, step: int) -> bool:
        """Selects the entry `step` positions further down in the list.

        Selects the first one if none is selected. Does not go past the ends.
        Returns whether the selection changed.
        """
        shown = self.shown
        if self.editing or not shown:
            return False
        index = shown.index(self.selected) if self.selected in shown else None
        new_index = 0 if index is None else min(max(index + step, 0), len(shown) - 1)
        if new_index == index:
            return False
        self.select_entry(shown[new_index])
        self.view.select_entry(shown[new_index])
        return True

    def show_selected_image(self) -> None:
        """Shows the image of the entry that is read in large."""
        image = self._image_of(self.selected)
        if image is not None:
            self.dialogs.show_photo(image)

    # ----------------------------------------------------------- writing / reading

    def set_writing(self, writing: bool) -> None:
        """Switches to writing a new entry, or back to reading.

        Going back asks first if there is something unsaved.
        """
        if writing:
            self.editing = True
            self.selected = None
            self.view.select_entry(None)
        elif self._check_discard() is not None:
            self._reset_draft()
            self.editing = False
            self.view.show_entry(self.selected, self._image_of(self.selected))
        self.view.show_mode(self.editing, self.photo_mode)

    def set_photo_mode(self, photo_mode: bool) -> None:
        """Switches to or from adding an image to the entry.

        Leaving the photo mode with an image asks first. The text is kept.
        """
        if self.editing and photo_mode != self.photo_mode:
            if photo_mode:
                self.photo_mode = True
            else:
                discard = self._check_discard(only_image=True)
                if discard is not None:
                    if discard:
                        self.draft_date = self._now()  # It was taken from the image
                    self.draft_image = None
                    self.photo_mode = False
                    self.view.show_draft_image(None)
                    self.view.show_draft_date(self.draft_date)
        self.view.show_mode(self.editing, self.photo_mode)

    def load_image(self, path: str, date_time: Optional[datetime] = None) -> bool:
        """Adds the image to the entry that is written and takes its date.

        Args:
            path: The image file.
            date_time: The date of the image, by default taken from the file.

        Returns whether the image was loaded.
        """
        if not (self.editing and self.photo_mode and is_supported_image(path)):
            return False
        self.draft_date = date_of_image_file(path) if date_time is None else date_time
        self.draft_image = path
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(path)
        return True

    def take_selfie(self) -> None:
        """Takes a picture with the webcam for the entry that is written."""
        if not self.editing:
            return
        self.set_photo_mode(True)
        now = self._now()
        path = os.path.join(self.temp.path, img_name_from_time(now) + "_Self.png")
        try:
            taken = self.dialogs.take_selfie(path)
        except NoWebcamError:
            self.dialogs.info(
                tr("message.no_webcam.text"), tr("message.no_webcam.title")
            )
            return
        if taken:
            self.load_image(path, now)

    def show_draft_image(self) -> None:
        """Shows the image of the entry that is written in large."""
        if self.draft_image is not None:
            self.dialogs.show_photo(self.draft_image)

    def change_date(self) -> None:
        """Lets the user choose another date for the entry that is written."""
        if not self.editing:
            return
        date_time = self.dialogs.pick_date(self._now())
        if date_time is not None:
            self.draft_date = date_time
            self.view.show_draft_date(date_time)

    def change_folder(self) -> None:
        """Lets the user choose another data folder."""
        path = self.dialogs.ask_folder()
        if not path:
            return
        folder = DataFolder(path)
        folder.create()
        self._use_folder(folder)
        self.draft_date = self._now()
        self.selected = None
        self.view.show_draft_date(self.draft_date)
        self.view.select_entry(None)
        self.reload_entries()
        if not self.editing:
            self.view.show_entry(None, None)

    def save(self) -> bool:
        """Saves the entry that is written. Returns whether it was saved.

        Shows a message instead if the text or, in the photo mode, the image is
        missing.
        """
        if not self.editing:
            return False
        text = self.view.get_text()
        if text == "":
            self.dialogs.info(tr("message.no_text.text"), tr("message.no_text.title"))
            return False

        if self.photo_mode:
            if self.draft_image is None:
                self.dialogs.info(
                    tr("message.no_image.text"), tr("message.no_image.title")
                )
                return False
            img_folder = self.folder.img_folder
            copied = copy_img_file_to_imgs(
                self.draft_image,
                img_folder,
                self.draft_date,
                lambda files: self.dialogs.choose_image(img_folder, files),
            )
            if copied is None:
                return False  # There is no decision, so keep the draft
            self.store.save_entry(text, self.draft_date, "photo", copied)
        else:
            self.store.save_entry(text, self.draft_date)

        # Start the next entry, in the same mode
        self.draft_image = None
        self.draft_date = self._now()
        self.view.set_text("")
        self.view.show_draft_image(None)
        self.view.show_draft_date(self.draft_date)
        self.reload_entries()
        return True

    def run_shortcut(self, action: str) -> None:
        """Does what a keyboard shortcut stands for, see `shortcuts.shortcut_for`."""
        if action in WRITING_ONLY and not self.editing:
            return
        handlers = {
            "new": lambda: self.set_writing(not self.editing),
            "save": self.save,
            "photo": lambda: self.set_photo_mode(not self.photo_mode),
            "date": self.change_date,
            "folder": self.change_folder,
            "selfie": self.take_selfie,
            "quit": self.view.close,
            # The list has the newest entry on top, so older ones are further down
            "prev": lambda: self.select_adjacent(1),
            "next": lambda: self.select_adjacent(-1),
        }
        handlers[action]()

    # ---------------------------------------------------------------------- helpers

    def _check_discard(self, only_image: bool = False) -> Optional[bool]:
        """Asks if the unsaved text and image of the draft may be thrown away.

        Args:
            only_image: Whether only an image counts as unsaved, not the text.

        Returns:
            None if the user wants to keep the draft, True if it may be
            discarded and False if there is nothing to lose.
        """
        if not self.editing:
            return False
        has_text = self.view.get_text() != ""
        has_image = self.draft_image is not None
        if not (has_image or (has_text and not only_image)):
            return False
        if only_image:
            text = tr("message.discard_image.text")
        elif has_image:
            text = tr("message.discard_text_image.text")
        else:
            text = tr("message.discard_text.text")
        if self.dialogs.confirm(
            text, tr("common.warning"), tr("common.discard"), tr("common.keep")
        ):
            return True
        return None

    def _reset_draft(self) -> None:
        """Throws away the text, the image, the chosen time and the photo mode."""
        self.draft_image = None
        self.photo_mode = False
        self.draft_date = self._now()
        self.view.set_text("")
        self.view.show_draft_image(None)
        self.view.show_draft_date(self.draft_date)

    def _image_of(self, entry: Optional[Entry]) -> Optional[str]:
        """The path of the image of an entry, None if it has none or it is missing."""
        if entry is None or not entry.photo:
            return None
        path = os.path.join(self.folder.img_folder, entry.photo)
        return path if os.path.isfile(path) else None

    def _use_folder(self, folder: DataFolder) -> None:
        """Takes the folder to read and write the entries and shows it."""
        self._folder = folder
        self._store = EntryStore(folder.xml_folder)
        self.view.show_folder(folder.path)

    def _show_entries(self) -> None:
        shown = self.shown
        selected = self.selected if self.selected in shown else None
        self.view.show_entries(shown, len(self.entries), selected)

    def _show_all(self) -> None:
        """Shows the whole state, e.g. at the start."""
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(self.draft_image)
        self.view.show_mode(self.editing, self.photo_mode)
        self.view.show_entry(self.selected, self._image_of(self.selected))
