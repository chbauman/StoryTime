"""The logic of the main window, without any GUI.

The `DiaryController` knows what the user can do and what happens then: writing
and reading entries, the draft with its image and date, the photo mode, the
list with the search, and saving. It does not know about widgets. Everything it
shows goes through a `View` and all questions to the user are asked through
`Dialogs`. The real ones are in `user_interface.py` and `dialogs.py`, the tests
use fake ones.
"""

import contextlib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Protocol

from story_time.dates import date_of_image_file, img_name_from_time
from story_time.entries import Entry, EntryStore, filter_entries
from story_time.folders import DataFolder, TempFolder, get_data_folder, save_data_folder
from story_time.images import copy_img_file_to_imgs, is_supported_image
from story_time.storage import open_store
from story_time.texts import tr


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

    def show_trash_view(self, active: bool, count: int) -> None:
        """Shows whether the list is the trash and how many entries are in it."""

    def show_editing_existing(self, existing: bool) -> None:
        """Shows whether a saved entry is changed instead of writing a new one."""

    def show_undo(self, message: Optional[str]) -> None:
        """Offers to undo the last discard with the message, hides it if None."""

    def show_folder(self, path: str) -> None:
        """Shows the folder with the data."""

    def close(self) -> None:
        """Closes the window."""


#: The text, date, image and photo mode of an entry before it is changed.
_Origin = tuple[str, datetime, Optional[str], bool]

#: The actions of the shortcuts that only make sense while writing.
WRITING_ONLY = {"save", "photo", "date", "selfie", "discard"}


@dataclass
class _Discarded:
    """What was thrown away from the draft, to bring it back."""

    image: Optional[str]
    date: datetime
    photo_mode: bool
    #: The text, None if it was not thrown away.
    text: Optional[str] = None
    #: Whether the draft was left to read an entry, so it has to be opened again.
    left_writing: bool = False


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
        #: Takes back the last discard or deletion while the user can undo it,
        #: returns whether it did.
        self._undo: Optional[Callable[[], bool]] = None
        #: Whether `_undo` is about the draft, which changes end.
        self._undo_of_draft = False
        #: The entries in the trash.
        self.trash: list[Entry] = []
        #: Whether the list shows the trash instead of the entries.
        self.show_trash = False
        #: The saved entry that is changed, None while a new one is written.
        self.editing_entry: Optional[Entry] = None
        self._edit_origin: Optional[_Origin] = None

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
        if not self._has_unsaved():
            return True
        return self._confirm_discard()

    def finish(self) -> None:
        """To be called when the app is closed."""
        if self._folder is not None:
            save_data_folder(self._folder)
        self.temp.remove()

    # --------------------------------------------------------------- entries / list

    @property
    def shown(self) -> list[Entry]:
        """The entries of the list matching the search, newest first."""
        return filter_entries(
            self.trash if self.show_trash else self.entries, self.query
        )

    def reload_entries(self) -> None:
        """Loads all entries and shows them in the list."""
        self.entries = self.store.load_all()
        self.trash = self.store.load_trash()
        # The selected entry may have been changed
        shown = self.trash if self.show_trash else self.entries
        self.selected = next(
            (e for e in shown if self.selected and e.id == self.selected.id), None
        )
        self.view.show_trash_view(self.show_trash, len(self.trash))
        self._show_entries()

    def set_query(self, query: str) -> None:
        """Searches the entries."""
        self.query = query
        self._show_entries()

    def select_entry(self, entry: Entry) -> None:
        """The user selected an entry in the list, to read it."""
        if self.editing:
            if self.editing_entry is not None:
                if not self.cancel_edit():
                    self.view.select_entry(self.selected)  # Keep editing
                    return
            else:
                self._leave_writing()
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

        Going back throws a new draft away, which can be undone. Stopping to
        change a saved entry asks first if there are changes.
        """
        if writing:
            if self.editing_entry is not None and not self.cancel_edit():
                self.view.show_mode(self.editing, self.photo_mode)
                return
            self._dismiss_draft_undo()
            if self._set_trash_view(False):
                self._show_entries()
            self.editing = True
            self.selected = None
            self.view.select_entry(None)
        elif self.editing:
            if self.editing_entry is not None:
                self.cancel_edit()
            else:
                self._leave_writing()
                self.view.show_entry(self.selected, self._image_of(self.selected))
        self.view.show_mode(self.editing, self.photo_mode)

    def set_photo_mode(self, photo_mode: bool) -> None:
        """Switches to or from adding an image to the entry.

        Leaving the photo mode removes the image, which can be undone. The text
        is kept.
        """
        if self.editing and photo_mode != self.photo_mode:
            if photo_mode:
                self.photo_mode = True
            else:
                self.remove_image(leave_photo_mode=True)
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
        self._dismiss_draft_undo()
        self.draft_date = date_of_image_file(path) if date_time is None else date_time
        self.draft_image = path
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(path)
        return True

    def take_selfie(self) -> None:
        """Takes a picture with the webcam for the entry that is written."""
        if not self.editing:
            return
        self._dismiss_draft_undo()
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
            self._dismiss_draft_undo()
            self.draft_date = date_time
            self.view.show_draft_date(date_time)

    def discard_draft(self) -> bool:
        """Throws away the text, the image and the chosen date of the draft.

        The user can undo it for a while. Returns whether there was something.
        For a saved entry that is changed, it stops changing it instead.
        """
        if self.editing_entry is not None:
            return self.cancel_edit()
        if not (self.editing and self._has_unsaved()):
            return False
        discarded = _Discarded(
            self.draft_image, self.draft_date, self.photo_mode, self.view.get_text()
        )
        self._clear_draft()
        self.photo_mode = discarded.photo_mode  # Keep adding an image
        self.view.show_mode(self.editing, self.photo_mode)
        self._offer_undo(tr("undo.draft_discarded"), lambda: self._restore(discarded))
        return True

    def remove_image(self, leave_photo_mode: bool = False) -> bool:
        """Removes only the image of the draft and keeps the text.

        The user can undo it for a while. Returns whether there was an image.
        """
        if not (self.editing and self.draft_image is not None):
            if leave_photo_mode:
                self.photo_mode = False
            return False
        discarded = _Discarded(self.draft_image, self.draft_date, self.photo_mode)
        self.draft_image = None
        self.draft_date = self._now()  # It was taken from the image
        self.photo_mode = self.photo_mode and not leave_photo_mode
        self.view.show_draft_image(None)
        self.view.show_draft_date(self.draft_date)
        self.view.show_mode(self.editing, self.photo_mode)
        self._offer_undo(tr("undo.image_removed"), lambda: self._restore(discarded))
        return True

    @property
    def can_undo(self) -> bool:
        """Whether a discard or deletion can be undone."""
        return self._undo is not None

    def undo_discard(self) -> bool:
        """Takes back the last discard or deletion. Returns whether it did."""
        undo = self._undo
        if undo is None:
            return False
        self._undo = None
        self.view.show_undo(None)
        return undo()

    def dismiss_undo(self) -> None:
        """The user can not undo the last discard any more, e.g. after a while."""
        if self._undo is not None:
            self._undo = None
            self.view.show_undo(None)

    def draft_edited(self) -> None:
        """The user changed the draft, so a discard of it can not be undone."""
        self._dismiss_draft_undo()

    # ------------------------------------------------- change / delete saved entries

    def edit_selected(self) -> None:
        """Starts to change the entry that is read."""
        entry = self.selected
        if self.editing or self.show_trash or entry is None:
            return
        self._dismiss_draft_undo()
        image = self._image_of(entry)
        self.editing_entry = entry
        self.editing = True
        self.photo_mode = entry.type == "photo"
        self.draft_image = image
        self.draft_date = entry.date_time
        self._edit_origin = (entry.text, entry.date_time, image, self.photo_mode)
        self.view.set_text(entry.text)
        self.view.show_draft_image(image)
        self.view.show_draft_date(entry.date_time)
        self.view.show_editing_existing(True)
        self.view.show_mode(self.editing, self.photo_mode)

    def cancel_edit(self) -> bool:
        """Stops changing a saved entry, asks first if something was changed.

        Returns whether the changes were thrown away, so the entry is read again.
        """
        if self.editing_entry is None:
            return False
        if self._has_unsaved() and not self._confirm_discard():
            return False
        self._finish_editing()
        self.view.show_mode(self.editing, self.photo_mode)
        self.view.show_entry(self.selected, self._image_of(self.selected))
        return True

    def delete_selected(self) -> bool:
        """Moves the entry that is read to the trash, which can be undone.

        Returns whether an entry was moved.
        """
        entry = self.selected
        if self.editing or self.show_trash or entry is None or entry.id is None:
            return False
        self.store.trash_entry(entry.id, self._now())
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        self._offer_undo(
            tr("undo.entry_deleted"), lambda: self._take_out(entry), draft=False
        )
        return True

    def set_trash_view(self, active: bool) -> None:
        """Shows the list of the entries in the trash, or the entries again."""
        if active != self.show_trash:
            if active and self.editing:
                if self.editing_entry is not None:
                    if not self.cancel_edit():
                        self.view.show_trash_view(self.show_trash, len(self.trash))
                        return
                else:
                    self._leave_writing()
                self.view.show_mode(self.editing, self.photo_mode)
            self._set_trash_view(active)
            self.dismiss_undo()
            self.selected = None
            self.view.select_entry(None)
            self.reload_entries()
            self.view.show_entry(None, None)

    def restore_selected(self) -> bool:
        """Takes the entry that is read out of the trash. Returns whether it did."""
        entry = self.selected
        if not self.show_trash or entry is None or entry.id is None:
            return False
        self.store.restore_entry(entry.id)
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        return True

    def delete_selected_forever(self) -> bool:
        """Removes the entry that is read from the trash for good, after asking."""
        entry = self.selected
        if not self.show_trash or entry is None or entry.id is None:
            return False
        if not self.dialogs.confirm(
            tr("message.delete_forever.text"),
            tr("common.warning"),
            tr("common.delete"),
            tr("common.keep"),
        ):
            return False
        self._delete_forever([entry])
        return True

    def empty_trash(self) -> bool:
        """Removes everything in the trash for good, after asking."""
        if not self.trash:
            return False
        if not self.dialogs.confirm(
            tr("message.empty_trash.text", count=len(self.trash)),
            tr("common.warning"),
            tr("common.delete"),
            tr("common.keep"),
        ):
            return False
        self._delete_forever(list(self.trash))
        return True

    def change_folder(self) -> None:
        """Lets the user choose another data folder."""
        path = self.dialogs.ask_folder()
        if not path:
            return
        folder = DataFolder(path)
        folder.create()
        self.dismiss_undo()  # It is about the old folder
        if self.editing_entry is not None:
            self._finish_editing()
            self.view.show_mode(self.editing, self.photo_mode)
        self.show_trash = False
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
        self._dismiss_draft_undo()
        text = self.view.get_text()
        if text == "":
            self.dialogs.info(tr("message.no_text.text"), tr("message.no_text.title"))
            return False

        image_name: Optional[str] = None
        if self.photo_mode:
            if self.draft_image is None:
                self.dialogs.info(
                    tr("message.no_image.text"), tr("message.no_image.title")
                )
                return False
            if (
                self.editing_entry is not None
                and self._edit_origin is not None
                and self.draft_image == self._edit_origin[2]
            ):
                image_name = self.editing_entry.photo  # Not changed, already there
            else:
                img_folder = self.folder.img_folder
                image_name = copy_img_file_to_imgs(
                    self.draft_image,
                    img_folder,
                    self.draft_date,
                    lambda files: self.dialogs.choose_image(img_folder, files),
                )
                if image_name is None:
                    return False  # There is no decision, so keep the draft
        entry_type = "text" if image_name is None else "photo"

        if self.editing_entry is not None and self.editing_entry.id is not None:
            saved = self.store.update_entry(
                self.editing_entry.id, text, self.draft_date, entry_type, image_name
            )
            self._finish_editing()
            self.selected = saved
            self.reload_entries()
            self.view.show_mode(self.editing, self.photo_mode)
            self.view.show_entry(self.selected, self._image_of(self.selected))
            return True
        self.store.save_entry(text, self.draft_date, entry_type, image_name)

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
            "discard": self.discard_draft,
            "edit": self.edit_selected,
            "folder": self.change_folder,
            "selfie": self.take_selfie,
            "quit": self.view.close,
            # The list has the newest entry on top, so older ones are further down
            "prev": lambda: self.select_adjacent(1),
            "next": lambda: self.select_adjacent(-1),
        }
        handlers[action]()

    # ---------------------------------------------------------------------- helpers

    def _has_unsaved(self) -> bool:
        """Whether the draft has something that would be lost.

        That is a text or an image of a new entry, or any change of an entry that
        is changed.
        """
        if not self.editing:
            return False
        if self._edit_origin is not None:
            return self._edit_origin != (
                self.view.get_text(),
                self.draft_date,
                self.draft_image,
                self.photo_mode,
            )
        return self.draft_image is not None or self.view.get_text() != ""

    def _confirm_discard(self) -> bool:
        """Asks if the unsaved draft or changes may be thrown away."""
        if self.editing_entry is not None:
            text = tr("message.discard_changes.text")
        elif self.draft_image is not None:
            text = tr("message.discard_text_image.text")
        else:
            text = tr("message.discard_text.text")
        return self.dialogs.confirm(
            text, tr("common.warning"), tr("common.discard"), tr("common.keep")
        )

    def _offer_undo(
        self, message: str, undo: Callable[[], bool], draft: bool = True
    ) -> None:
        self._undo = undo
        self._undo_of_draft = draft
        self.view.show_undo(message)

    def _dismiss_draft_undo(self) -> None:
        """Ends the undo of a discard of the draft, one of a deletion stays."""
        if self._undo_of_draft:
            self.dismiss_undo()

    def _restore(self, discarded: _Discarded) -> bool:
        """Brings back what a discard threw away from the draft."""
        if discarded.left_writing:
            self.editing = True
            self.selected = None
            self.view.select_entry(None)
        elif not self.editing:
            return False
        if discarded.text is not None:
            self.view.set_text(discarded.text)
        self.draft_image = discarded.image
        self.draft_date = discarded.date
        self.photo_mode = discarded.photo_mode
        self.view.show_draft_image(self.draft_image)
        self.view.show_draft_date(self.draft_date)
        self.view.show_mode(self.editing, self.photo_mode)
        return True

    def _take_out(self, entry: Entry) -> bool:
        """Takes a deleted entry out of the trash and shows it if possible."""
        if entry.id is None or self.show_trash:
            return False
        self.store.restore_entry(entry.id)
        self.reload_entries()
        if not self.editing:
            self.selected = next((e for e in self.entries if e.id == entry.id), None)
            self.view.select_entry(self.selected)
            self.view.show_entry(self.selected, self._image_of(self.selected))
        return True

    def _delete_forever(self, entries: list[Entry]) -> None:
        """Removes entries of the trash and their images, if nothing else uses them."""
        self.store.delete_forever([e.id for e in entries if e.id is not None])
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        used = {e.photo for e in self.entries + self.trash}
        for entry in entries:
            if entry.photo and entry.photo not in used:
                # It may be gone already
                with contextlib.suppress(OSError):
                    os.remove(os.path.join(self.folder.img_folder, entry.photo))

    def _set_trash_view(self, active: bool) -> bool:
        """Switches the list between the entries and the trash, returns if it did."""
        if active == self.show_trash:
            return False
        self.show_trash = active
        self.view.show_trash_view(active, len(self.trash))
        return True

    def _finish_editing(self) -> None:
        """Ends changing a saved entry, the changes are thrown away."""
        self.editing_entry = None
        self._edit_origin = None
        self._clear_draft()
        self.editing = False
        self.view.show_editing_existing(False)

    def _leave_writing(self) -> None:
        """Goes from writing to reading, the draft can be undone if it had content."""
        if self._has_unsaved():
            discarded = _Discarded(
                self.draft_image,
                self.draft_date,
                self.photo_mode,
                self.view.get_text(),
                left_writing=True,
            )
            self._offer_undo(
                tr("undo.draft_discarded"), lambda: self._restore(discarded)
            )
        else:
            self._dismiss_draft_undo()
        self._clear_draft()
        self.editing = False

    def _clear_draft(self) -> None:
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
        self._store = open_store(folder)
        self.view.show_folder(folder.path)

    def _show_entries(self) -> None:
        shown = self.shown
        selected = self.selected if self.selected in shown else None
        total = len(self.trash if self.show_trash else self.entries)
        self.view.show_entries(shown, total, selected)

    def _show_all(self) -> None:
        """Shows the whole state, e.g. at the start."""
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(self.draft_image)
        self.view.show_mode(self.editing, self.photo_mode)
        self.view.show_entry(self.selected, self._image_of(self.selected))
