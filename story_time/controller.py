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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

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

    def ask_folder(self) -> str | None:
        """Asks for the folder with the data, `None` if there is none chosen."""

    def confirm(self, text: str, title: str, ok_label: str, cancel_label: str) -> bool:
        """Asks a question, returns whether the user chose the OK label."""

    def info(self, text: str, title: str) -> None:
        """Shows a message."""

    def choose_image(self, img_folder: str, files: list[str]) -> int | None:
        """Asks which one of the images with the same date to use for the entry.

        The images are the files with the given names in the image folder.

        Returns the index of the chosen image, `images.NEW_IMAGE` to add the new
        image anyway and `None` if there is no decision.
        """

    def pick_image_file(self) -> str | None:
        """Lets the user choose an image file, `None` if the user cancels."""

    def pick_date(self, start: datetime) -> datetime | None:
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

    def show_mode(self, editing: bool) -> None:
        """Shows the page to write or to read."""

    def show_draft_image(self, path: str | None) -> None:
        """Shows the image of the entry that is written, none if `path` is None."""

    def show_draft_date(self, date_time: datetime) -> None:
        """Shows the date of the entry that is written."""

    def show_entry(self, entry: Entry | None, image: str | None) -> None:
        """Shows an entry with its image, nothing if the entry is None."""

    def show_entries(
        self,
        shown: list[Entry],
        trash: list[Entry],
        total: int,
        selected: Entry | None,
    ) -> None:
        """Shows the list of entries and, below, the entries in the trash.

        The selected entry is selected if it is in one of them. `total` is the
        number of all entries and the entries in the trash, also the ones that
        do not match the search.
        """

    def select_entry(self, entry: Entry | None) -> None:
        """Selects an entry in the list, deselects if it is None."""

    def show_editing_existing(self, existing: bool) -> None:
        """Shows whether a saved entry is changed instead of writing a new one."""

    def show_history(self, undo: str | None, redo: str | None) -> None:
        """Shows what can be undone and redone, with None if nothing."""

    def show_folder(self, path: str) -> None:
        """Shows the folder with the data."""

    def close(self) -> None:
        """Closes the window."""


#: The text, date and image of an entry before it is changed.
_Origin = tuple[str, datetime, str | None]

#: The actions of the shortcuts that only make sense while writing.
WRITING_ONLY = {"save", "upload", "date", "selfie", "discard"}

#: How many steps the user can undo.
MAX_HISTORY = 50


@dataclass
class _Step:
    """A change the user can undo and redo."""

    message: str
    undo: Callable[[], bool]
    redo: Callable[[], bool]
    #: Whether it is about the draft, so it ends when the draft is changed.
    of_draft: bool = False


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

        #: Whether an entry is written, otherwise the entries are read.
        self.editing = True
        #: The image of the entry that is written, if one is loaded.
        self.draft_image: str | None = None
        #: The date of the entry that is written.
        self.draft_date = now()

        self._folder: DataFolder | None = None
        self._store: EntryStore | None = None
        #: The folder for the pictures taken with the webcam until they are saved.
        self.temp = TempFolder()

        #: The entries that are not in the trash.
        self.entries: list[Entry] = []
        #: The entries in the trash.
        self.trash: list[Entry] = []
        self.query = ""
        #: The entry that is shown on the page to read, in the trash or not.
        self.selected: Entry | None = None
        #: The saved entry that is changed, None while a new one is written.
        self.editing_entry: Entry | None = None
        self._edit_origin: _Origin | None = None
        #: What can be undone, the last step last, and what can be redone.
        self._done: list[_Step] = []
        self._undone: list[_Step] = []

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
        """The entries matching the search, newest first."""
        return filter_entries(self.entries, self.query)

    @property
    def shown_trash(self) -> list[Entry]:
        """The entries in the trash matching the search, the last deleted first."""
        return filter_entries(self.trash, self.query)

    def reload_entries(self) -> None:
        """Loads all entries and shows them in the list."""
        self.entries = self.store.load_all()
        self.trash = self.store.load_trash()
        # The selected entry may have been changed or moved
        selected = self.selected
        self.selected = next(
            (e for e in self.entries + self.trash if selected and e.id == selected.id),
            None,
        )
        self._show_entries()

    def set_query(self, query: str) -> None:
        """Searches the entries."""
        self.query = query
        self._show_entries()

    def select_entry(self, entry: Entry) -> None:
        """The user selected an entry in the list, to read it.

        Asks first if a draft or the changes of an entry would be lost.
        """
        if self.editing and not self._leave_writing():
            self.view.select_entry(self.selected)  # Keep writing
            return
        self.selected = entry
        self.view.show_mode(self.editing)
        self.view.show_entry(entry, self._image_of(entry))

    def select_adjacent(self, step: int) -> bool:
        """Selects the entry `step` positions further down in the list.

        Selects the first one if none is selected. Does not go past the ends.
        The entries in the trash come after the others.
        Returns whether the selection changed.
        """
        shown = self.shown + self.shown_trash
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

        Going back asks first if a draft or the changes of an entry would be lost.
        """
        if writing:
            if self.editing and not self._leave_writing():
                self.view.show_mode(self.editing)
                return
            self.editing = True
            self.selected = None
            self.view.select_entry(None)
        elif self.editing:
            if self._leave_writing():
                self.view.show_entry(self.selected, self._image_of(self.selected))
        self.view.show_mode(self.editing)

    def load_image(self, path: str, date_time: datetime | None = None) -> bool:
        """Adds the image to the entry that is written and takes its date.

        Args:
            path: The image file.
            date_time: The date of the image, by default taken from the file.

        Returns whether the image was loaded.
        """
        if not (self.editing and is_supported_image(path)):
            return False
        self._end_draft_steps()
        self.draft_date = date_of_image_file(path) if date_time is None else date_time
        self.draft_image = path
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(path)
        return True

    def upload_image(self) -> bool:
        """Lets the user choose an image file for the entry that is written."""
        if not self.editing:
            return False
        path = self.dialogs.pick_image_file()
        if path is None:
            return False
        if self.load_image(path):
            return True
        self.dialogs.info(tr("message.no_image_file.text"), tr("common.warning"))
        return False

    def take_selfie(self) -> None:
        """Takes a picture with the webcam for the entry that is written."""
        if not self.editing:
            return
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
        date_time = self.dialogs.pick_date(self.draft_date)
        if date_time is not None:
            self._end_draft_steps()
            self.draft_date = date_time
            self.view.show_draft_date(date_time)

    def draft_edited(self) -> None:
        """The user changed the text, so steps about the draft can not be undone."""
        self._end_draft_steps()

    def discard_draft(self) -> bool:
        """Throws away the text, the image and the chosen date of the draft.

        The user can undo it. Returns whether there was something. For a saved
        entry that is changed, it stops changing it instead.
        """
        if self.editing_entry is not None:
            return self.cancel_edit()
        if not (self.editing and self._has_unsaved()):
            return False
        text, image, date = self.view.get_text(), self.draft_image, self.draft_date

        def discard() -> bool:
            if not self.editing:
                return False
            self._clear_draft()
            return True

        def restore() -> bool:
            if not self.editing:
                return False
            self.view.set_text(text)
            self._set_draft_image(image, date)
            return True

        discard()
        self._record(_Step(tr("undo.draft_discarded"), restore, discard, True))
        return True

    def remove_image(self) -> bool:
        """Removes only the image of the draft and keeps the text.

        The user can undo it. Returns whether there was an image.
        """
        if not (self.editing and self.draft_image is not None):
            return False
        image, date = self.draft_image, self.draft_date

        def remove() -> bool:
            if not self.editing:
                return False
            self._set_draft_image(None, self._now())  # The date was the image's
            return True

        def restore() -> bool:
            if not self.editing:
                return False
            self._set_draft_image(image, date)
            return True

        remove()
        self._record(_Step(tr("undo.image_removed"), restore, remove, True))
        return True

    # ------------------------------------------------------------- undo / redo

    @property
    def can_undo(self) -> bool:
        """Whether there is something to undo."""
        return bool(self._done)

    @property
    def can_redo(self) -> bool:
        """Whether there is something to redo."""
        return bool(self._undone)

    def undo(self) -> bool:
        """Takes back the last change that was not undone. Returns whether it did."""
        if not self._done:
            return False
        step = self._done.pop()
        done = step.undo()
        if done:
            self._undone.append(step)
        self._show_history()
        return done

    def redo(self) -> bool:
        """Does the last undone change again. Returns whether it did."""
        if not self._undone:
            return False
        step = self._undone.pop()
        done = step.redo()
        if done:
            self._done.append(step)
        self._show_history()
        return done

    # ------------------------------------------------- change / delete saved entries

    def edit_selected(self) -> None:
        """Starts to change the entry that is read."""
        entry = self.selected
        if self.editing or entry is None or entry.deleted_at is not None:
            return
        self._end_draft_steps()
        image = self._image_of(entry)
        self.editing_entry = entry
        self.editing = True
        self.draft_image = image
        self.draft_date = entry.date_time
        self._edit_origin = (entry.text, entry.date_time, image)
        self.view.set_text(entry.text)
        self.view.show_draft_image(image)
        self.view.show_draft_date(entry.date_time)
        self.view.show_editing_existing(True)
        self.view.show_mode(self.editing)

    def cancel_edit(self) -> bool:
        """Stops changing a saved entry, asks first if something was changed.

        Returns whether the changes were thrown away, so the entry is read again.
        """
        if self.editing_entry is None:
            return False
        if self._has_unsaved() and not self._confirm_discard():
            return False
        self._finish_editing()
        self.view.show_mode(self.editing)
        self.view.show_entry(self.selected, self._image_of(self.selected))
        return True

    def delete_selected(self) -> bool:
        """Moves the entry that is read to the trash, which can be undone.

        Returns whether an entry was moved.
        """
        entry = self.selected
        if self.editing or entry is None or entry.deleted_at is not None:
            return False
        if entry.id is None or not self._move_to_trash(entry.id):
            return False
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        self._record(
            _Step(
                tr("undo.entry_deleted"),
                lambda: self._take_out(entry),
                lambda: self._put_in_trash(entry),
            )
        )
        return True

    def restore_selected(self) -> bool:
        """Takes the entry that is read out of the trash. Returns whether it did."""
        entry = self.selected
        if entry is None or entry.deleted_at is None or entry.id is None:
            return False
        if not self._take_out_of_trash(entry.id):
            return False
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        self._record(
            _Step(
                tr("undo.entry_restored"),
                lambda: self._put_in_trash(entry),
                lambda: self._take_out(entry, select=False),
            )
        )
        return True

    def delete_selected_forever(self) -> bool:
        """Removes the entry that is read from the trash for good, after asking."""
        entry = self.selected
        if entry is None or entry.deleted_at is None or entry.id is None:
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
        # The steps are about the old folder
        self._done.clear()
        self._undone.clear()
        if self.editing_entry is not None:
            self._finish_editing()
            self.view.show_mode(self.editing)
        self._use_folder(folder)
        self.draft_date = self._now()
        self.selected = None
        self.view.show_draft_date(self.draft_date)
        self.view.select_entry(None)
        self.reload_entries()
        self._show_history()
        if not self.editing:
            self.view.show_entry(None, None)

    def save(self) -> bool:
        """Saves the entry that is written. Returns whether it was saved.

        An entry with an image is a photo entry. Shows a message instead if the
        text is missing.
        """
        if not self.editing:
            return False
        self._end_draft_steps()
        text = self.view.get_text()
        if text == "":
            self.dialogs.info(tr("message.no_text.text"), tr("message.no_text.title"))
            return False

        image_name: str | None = None
        if (
            self.editing_entry is not None
            and self._edit_origin is not None
            and self.draft_image == self._edit_origin[2]
        ):
            # The image was not changed, so it is already there (or missing)
            image_name = self.editing_entry.photo
        elif self.draft_image is not None:
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
            self.view.show_mode(self.editing)
            self.view.show_entry(self.selected, self._image_of(self.selected))
            return True
        self.store.save_entry(text, self.draft_date, entry_type, image_name)

        # Start the next entry
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
            "upload": self.upload_image,
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

    def _leave_writing(self) -> bool:
        """Goes from writing to reading, after asking if something would be lost.

        Returns whether the draft was left.
        """
        if self._has_unsaved() and not self._confirm_discard():
            return False
        if self.editing_entry is not None:
            self._finish_editing()
        else:
            self._end_draft_steps()
            self._clear_draft()
            self.editing = False
        return True

    def _finish_editing(self) -> None:
        """Ends changing a saved entry, the changes are thrown away."""
        self._end_draft_steps()
        self.editing_entry = None
        self._edit_origin = None
        self._clear_draft()
        self.editing = False
        self.view.show_editing_existing(False)

    def _clear_draft(self) -> None:
        """Throws away the text, the image and the chosen time."""
        self._set_draft_image(None, self._now())
        self.view.set_text("")

    def _set_draft_image(self, path: str | None, date_time: datetime) -> None:
        self.draft_image = path
        self.draft_date = date_time
        self.view.show_draft_image(path)
        self.view.show_draft_date(date_time)

    def _record(self, step: _Step) -> None:
        """Remembers a change the user can undo, which ends what could be redone."""
        self._done.append(step)
        del self._done[:-MAX_HISTORY]
        self._undone.clear()
        self._show_history()

    def _end_draft_steps(self) -> None:
        """Forgets the steps about the draft, as the draft is not the same any more."""
        before = (len(self._done), len(self._undone))
        self._done = [s for s in self._done if not s.of_draft]
        self._undone = [s for s in self._undone if not s.of_draft]
        if before != (len(self._done), len(self._undone)):
            self._show_history()

    def _show_history(self) -> None:
        self.view.show_history(
            self._done[-1].message if self._done else None,
            self._undone[-1].message if self._undone else None,
        )

    def _move_to_trash(self, entry_id: int) -> bool:
        try:
            self.store.trash_entry(entry_id, self._now())
        except KeyError:
            return False
        return True

    def _take_out_of_trash(self, entry_id: int) -> bool:
        try:
            self.store.restore_entry(entry_id)
        except KeyError:
            return False
        return True

    def _take_out(self, entry: Entry, select: bool = True) -> bool:
        """Takes a deleted entry out of the trash and shows it if possible."""
        if entry.id is None or not self._take_out_of_trash(entry.id):
            return False
        self._show_changed(entry, select)
        return True

    def _put_in_trash(self, entry: Entry) -> bool:
        """Moves an entry to the trash again, e.g. to redo deleting it."""
        if entry.id is None or not self._move_to_trash(entry.id):
            return False
        self._show_changed(entry, False)
        return True

    def _show_changed(self, entry: Entry, select: bool) -> None:
        """Shows the list after an entry moved to or from the trash by undo/redo.

        An entry that was taken out is selected if the user is not writing.
        """
        was_selected = self.selected is not None and self.selected.id == entry.id
        if was_selected:
            self.selected = None
        self.reload_entries()
        if self.editing:
            return
        if select:
            self.selected = next((e for e in self.entries if e.id == entry.id), None)
            self.view.select_entry(self.selected)
            self.view.show_entry(self.selected, self._image_of(self.selected))
        elif was_selected:
            self.view.select_entry(None)
            self.view.show_entry(None, None)

    def _delete_forever(self, entries: list[Entry]) -> None:
        """Removes entries of the trash and their images, if nothing else uses them.

        This can not be undone, so the steps about these entries are forgotten.
        """
        self.store.delete_forever([e.id for e in entries if e.id is not None])
        self._done.clear()
        self._undone.clear()
        self.selected = None
        self.reload_entries()
        self.view.show_entry(None, None)
        self._show_history()
        used = {e.photo for e in self.entries + self.trash}
        for entry in entries:
            if entry.photo and entry.photo not in used:
                # It may be gone already
                with contextlib.suppress(OSError):
                    os.remove(os.path.join(self.folder.img_folder, entry.photo))

    def _image_of(self, entry: Entry | None) -> str | None:
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
        shown, trash = self.shown, self.shown_trash
        selected = self.selected if self.selected in shown + trash else None
        total = len(self.entries) + len(self.trash)
        self.view.show_entries(shown, trash, total, selected)

    def _show_all(self) -> None:
        """Shows the whole state, e.g. at the start."""
        self.view.show_draft_date(self.draft_date)
        self.view.show_draft_image(self.draft_image)
        self.view.show_mode(self.editing)
        self.view.show_entry(self.selected, self._image_of(self.selected))
        self._show_history()
