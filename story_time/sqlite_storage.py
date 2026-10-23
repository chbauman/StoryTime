"""Stores the entries of the diary in a SQLite database.

Compared to one XML file per year that is rewritten for each entry, a database

- writes in transactions, so a crash never leaves half a file,
- gives each entry an id, so entries with the same date and time can be told
  apart, and can be edited or deleted later,
- can search and sort without reading everything.

It only uses the `sqlite3` module of Python and has no dependency on the GUI.
"""

import os
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from story_time.entries import Entry

#: The version of the layout of the tables, kept in the database with
#: `PRAGMA user_version`, to be able to change them later.
SCHEMA_VERSION = 1

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_time TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('text', 'photo')),
    text TEXT NOT NULL,
    photo TEXT
);
CREATE INDEX IF NOT EXISTS entries_date_time ON entries (date_time);
PRAGMA user_version = {SCHEMA_VERSION};
"""


_INSERT = "INSERT INTO entries (date_time, type, text, photo) VALUES (?, ?, ?, ?)"


class StorageError(RuntimeError):
    """The database cannot be used."""


def _to_text(date_time: datetime) -> str:
    """The date and time as text, which sorts the same as the dates."""
    return date_time.isoformat(timespec="seconds")


def _entry_of(row: tuple) -> Entry:
    entry_id, date_time, entry_type, text, photo = row
    return Entry(datetime.fromisoformat(date_time), entry_type, text, photo, entry_id)


class SqliteEntryStore:
    """The entries of the diary, kept in a SQLite database file."""

    _COLUMNS = "id, date_time, type, text, photo"

    def __init__(self, db_file: str) -> None:
        """Opens the database, creates it if there is none yet.

        Raises:
            StorageError: If the file is not a database of this app or was written
                by a newer version of it.
        """
        self.db_file = db_file
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
        try:
            with self._connect() as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version > SCHEMA_VERSION:
                    raise StorageError(
                        f"{db_file} was written by a newer version of the app."
                    )
                conn.executescript(_SCHEMA)
        except sqlite3.DatabaseError as error:
            raise StorageError(
                f"{db_file} is not a usable database: {error}"
            ) from error

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """A connection that commits what was done, or undoes all if it failed."""
        conn = sqlite3.connect(self.db_file)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _check(entry_type: str, img_filename: Optional[str]) -> Optional[str]:
        """Checks the type of an entry, returns the name of its image file."""
        if entry_type == "text":
            return None
        if entry_type == "photo":
            assert img_filename is not None, "Need to specify image filename!"
            return os.path.basename(img_filename)
        raise ValueError(f"Entry of type: {entry_type} is not supported!")

    def save_entry(
        self,
        comm: str,
        date_time: datetime,
        entry_type: str = "text",
        img_filename: Optional[str] = None,
    ) -> Entry:
        """Adds an entry and returns it, with its id.

        Args:
            comm: The text for the entry.
            date_time: The date and time of the entry.
            entry_type: The type of the entry, either "text" or "photo".
            img_filename: For a photo the image file, only its name is stored.
        """
        photo = self._check(entry_type, img_filename)
        with self._connect() as conn:
            cursor = conn.execute(
                _INSERT,
                (_to_text(date_time), entry_type, comm, photo),
            )
        return Entry(date_time, entry_type, comm, photo, cursor.lastrowid)

    def add_entries(self, entries: Iterable[Entry]) -> int:
        """Adds many entries at once, all or none of them. Returns how many.

        The entries get new ids in the order they are given in.
        """
        rows = [
            (_to_text(e.date_time), e.type, e.text, self._check(e.type, e.photo))
            for e in entries
        ]
        with self._connect() as conn:
            conn.executemany(
                _INSERT,
                rows,
            )
        return len(rows)

    def load_all(self) -> list[Entry]:
        """Loads all entries, newest first.

        Entries with the same time are in the order they were added.
        """
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {self._COLUMNS} FROM entries ORDER BY date_time DESC, id ASC"
            ).fetchall()
        return [_entry_of(row) for row in rows]
