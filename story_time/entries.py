"""The entries of the diary, independent of how they are stored.

There is no dependency on the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class Entry:
    """An entry of the diary."""

    date_time: datetime
    type: str  #: Either "text" or "photo".
    text: str
    photo: str | None = None  #: For photo entries the file name in the Img folder.
    #: Identifies the entry in its store, None if it was not stored (yet).
    id: int | None = None

    @property
    def first_line(self) -> str:
        """The first non-empty line of the text."""
        for line in self.text.splitlines():
            if line.strip():
                return line.strip()
        return ""


class EntryStore(Protocol):
    """Where the entries are kept."""

    def save_entry(
        self,
        comm: str,
        date_time: datetime,
        entry_type: str = "text",
        img_filename: str | None = None,
    ) -> Entry:
        """Adds an entry and returns it.

        Args:
            comm: The text for the entry.
            date_time: The date and time of the entry.
            entry_type: The type of the entry, either "text" or "photo".
            img_filename: For a photo the image file, only its name is stored.
        """

    def load_all(self) -> list[Entry]:
        """Loads all entries, newest first."""


def filter_entries(entries: list[Entry], query: str) -> list[Entry]:
    """Returns the entries whose text contains all words of the query.

    The search ignores the case. All entries are returned for an empty query.
    """
    words = query.lower().split()
    return [e for e in entries if all(w in e.text.lower() for w in words)]


def group_by_month(entries: list[Entry]) -> list[tuple[tuple[int, int], list[Entry]]]:
    """Groups entries by (year, month), in the order of the entries."""
    groups: list[tuple[tuple[int, int], list[Entry]]] = []
    for entry in entries:
        key = (entry.date_time.year, entry.date_time.month)
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(entry)
    return groups
