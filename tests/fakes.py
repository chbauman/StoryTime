"""Fake view and dialogs to test the controller without any GUI."""

import shutil
from collections import deque
from datetime import datetime
from typing import Optional

from story_time.images import NEW_IMAGE
from story_time.xml_storage import Entry


class FakeView:
    """Remembers what the controller showed."""

    def __init__(self) -> None:
        self.text = ""
        self.editing: Optional[bool] = None
        self.draft_image: Optional[str] = None
        self.draft_date: Optional[datetime] = None
        #: The entry on the page to read and the path of its image.
        self.entry: Optional[Entry] = None
        self.entry_image: Optional[str] = None
        self.shown: list[Entry] = []
        self.trash: list[Entry] = []
        self.total = 0
        self.selected: Optional[Entry] = None
        self.folder: Optional[str] = None
        self.closed = False
        #: What the buttons to undo and redo say, None if they are disabled.
        self.undo: Optional[str] = None
        self.redo: Optional[str] = None
        self.editing_existing = False

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text

    def show_mode(self, editing: bool) -> None:
        self.editing = editing

    def show_draft_image(self, path: Optional[str]) -> None:
        self.draft_image = path

    def show_draft_date(self, date_time: datetime) -> None:
        self.draft_date = date_time

    def show_entry(self, entry: Optional[Entry], image: Optional[str]) -> None:
        self.entry = entry
        self.entry_image = image

    def show_entries(
        self,
        shown: list[Entry],
        trash: list[Entry],
        total: int,
        selected: Optional[Entry],
    ) -> None:
        self.shown = shown
        self.trash = trash
        self.total = total
        self.selected = selected

    def select_entry(self, entry: Optional[Entry]) -> None:
        self.selected = entry

    def show_editing_existing(self, existing: bool) -> None:
        self.editing_existing = existing

    def show_history(self, undo: Optional[str], redo: Optional[str]) -> None:
        self.undo = undo
        self.redo = redo

    def show_folder(self, path: str) -> None:
        self.folder = path

    def close(self) -> None:
        self.closed = True


class FakeDialogs:
    """Gives the prepared answers and remembers the questions."""

    def __init__(self) -> None:
        #: The answers for `confirm`, a question without an answer fails the test.
        self.confirm_answers: deque[bool] = deque()
        self.confirms: list[tuple[str, str, str, str]] = []
        self.infos: list[tuple[str, str]] = []
        self.folder: Optional[str] = None
        self.folder_asked = 0
        self.image_choice: Optional[int] = NEW_IMAGE
        self.image_choices: list[tuple[str, list[str]]] = []
        self.date: Optional[datetime] = None
        self.date_starts: list[datetime] = []
        #: The picture the "webcam" takes, None if the user cancels.
        self.selfie_source: Optional[str] = None
        #: Raises the error for a missing webcam instead.
        self.no_webcam = False
        self.selfie_targets: list[str] = []
        #: The file the user "picks" to upload, None if the user cancels.
        self.image_file: Optional[str] = None
        self.image_file_asked = 0
        self.photos: list[str] = []

    def answer_confirm(self, *answers: bool) -> None:
        self.confirm_answers.extend(answers)

    def ask_folder(self) -> Optional[str]:
        self.folder_asked += 1
        return self.folder

    def confirm(self, text: str, title: str, ok_label: str, cancel_label: str) -> bool:
        self.confirms.append((text, title, ok_label, cancel_label))
        assert self.confirm_answers, f"Unexpected question: {text}"
        return self.confirm_answers.popleft()

    def info(self, text: str, title: str) -> None:
        self.infos.append((text, title))

    def choose_image(self, img_folder: str, files: list[str]) -> Optional[int]:
        self.image_choices.append((img_folder, files))
        return self.image_choice

    def pick_image_file(self) -> Optional[str]:
        self.image_file_asked += 1
        return self.image_file

    def pick_date(self, start: datetime) -> Optional[datetime]:
        self.date_starts.append(start)
        return self.date

    def take_selfie(self, save_to: str) -> bool:
        from story_time.controller import NoWebcamError

        self.selfie_targets.append(save_to)
        if self.no_webcam:
            raise NoWebcamError("No webcam")
        if self.selfie_source is None:
            return False
        shutil.copy(self.selfie_source, save_to)
        return True

    def show_photo(self, path: str) -> None:
        self.photos.append(path)
