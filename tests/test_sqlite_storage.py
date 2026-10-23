import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from unittest import TestCase

from story_time.entries import Entry
from story_time.sqlite_storage import SCHEMA_VERSION, SqliteEntryStore, StorageError


class TestSqliteEntryStore(TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="story_time_test_db_")
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.db_file = os.path.join(self.folder, "diary.sqlite")
        self.store = SqliteEntryStore(self.db_file)

    def test_new_database_is_empty(self):
        assert self.store.load_all() == []
        assert os.path.isfile(self.db_file)

    def test_database_in_a_new_folder(self):
        store = SqliteEntryStore(os.path.join(self.folder, "a", "b", "diary.sqlite"))
        assert store.load_all() == []

    def test_text_entry(self):
        date_time = datetime(2020, 12, 2, 5, 31, 7)
        saved = self.store.save_entry("Hello", date_time)
        assert saved == Entry(date_time, "text", "Hello", None, saved.id)
        assert isinstance(saved.id, int)
        assert self.store.load_all() == [saved]

    def test_photo_entry(self):
        date_time = datetime(2020, 12, 2, 5, 31)
        saved = self.store.save_entry("A photo", date_time, "photo", "IMG_1.jpg")
        assert (saved.type, saved.photo) == ("photo", "IMG_1.jpg")
        assert self.store.load_all() == [saved]

    def test_only_the_name_of_the_image_is_stored(self):
        saved = self.store.save_entry(
            "A photo", datetime(2020, 1, 2, 3), "photo", "/some/where/a.jpg"
        )
        assert saved.photo == "a.jpg"
        assert self.store.load_all()[0].photo == "a.jpg"

    def test_invalid_entries_are_refused_and_change_nothing(self):
        self.store.save_entry("Valid", datetime(2020, 1, 2, 3))
        with self.assertRaises(ValueError):
            self.store.save_entry("Text", datetime(2020, 1, 2, 3), "blah", "a.jpg")
        with self.assertRaises(AssertionError):
            self.store.save_entry("Text", datetime(2020, 1, 2, 3), "photo")
        assert [e.text for e in self.store.load_all()] == ["Valid"]

    def test_ids_are_unique_and_not_reused(self):
        date_time = datetime(2020, 1, 2, 3)
        ids = [self.store.save_entry(f"Entry {k}", date_time).id for k in range(5)]
        assert len(set(ids)) == 5 and ids == sorted(ids)

    def test_entries_with_the_same_time_stay_apart(self):
        date_time = datetime(2020, 1, 2, 3, 4, 5)
        first = self.store.save_entry("Same", date_time)
        second = self.store.save_entry("Same", date_time)
        loaded = self.store.load_all()
        assert loaded == [first, second]  # in the order they were added
        assert first != second

    def test_newest_first_over_the_years(self):
        for text, date_time in [
            ("Middle", datetime(2020, 6, 2, 10)),
            ("Old", datetime(2019, 1, 5, 8, 15, 30)),
            ("New", datetime(2021, 2, 1, 23, 59, 59)),
            ("Same day later", datetime(2020, 6, 2, 11)),
        ]:
            self.store.save_entry(text, date_time)
        texts = [e.text for e in self.store.load_all()]
        assert texts == ["New", "Same day later", "Middle", "Old"]

    def test_special_texts(self):
        texts = [
            "Umlauts: \u00e4\u00f6\u00fc \u00df, \u20ac, \u65e5\u672c, \U0001f600",
            "Line 1\n\nLine 3\r\nLine 4",
            "Quotes ' \" and ; -- DROP TABLE entries; --",
            "x" * 100_000,
            "",
        ]
        for text in texts:
            self.store.save_entry(text, datetime(2020, 1, 2, 3))
        assert sorted(e.text for e in self.store.load_all()) == sorted(texts)

    def test_entries_are_kept_when_reopened(self):
        saved = self.store.save_entry("Kept", datetime(2020, 1, 2, 3))
        again = SqliteEntryStore(self.db_file)
        assert again.load_all() == [saved]
        # And opening it did not change what is in it
        assert len(SqliteEntryStore(self.db_file).load_all()) == 1

    def test_add_entries_at_once(self):
        entries = [
            Entry(datetime(2020, 1, k), "text", f"Entry {k}") for k in range(1, 6)
        ]
        assert self.store.add_entries(entries) == 5
        loaded = self.store.load_all()
        assert [e.text for e in loaded] == [f"Entry {k}" for k in range(5, 0, -1)]
        assert all(e.id is not None for e in loaded)

    def test_add_entries_is_all_or_nothing(self):
        entries = [
            Entry(datetime(2020, 1, 1), "text", "Fine"),
            Entry(datetime(2020, 1, 2), "photo", "No image", None),
        ]
        with self.assertRaises(AssertionError):
            self.store.add_entries(entries)
        assert self.store.load_all() == []

    def test_a_failed_save_leaves_the_database_intact(self):
        self.store.save_entry("Before", datetime(2020, 1, 2, 3))
        # The type is checked by the database as well
        raises = self.assertRaises(sqlite3.IntegrityError)
        with raises, self.store._connect() as conn:
            conn.execute(
                "INSERT INTO entries (date_time, type, text) "
                "VALUES ('2020-01-01T00:00:00', 'video', 'x')"
            )
        assert [e.text for e in self.store.load_all()] == ["Before"]
        self.store.save_entry("After", datetime(2020, 1, 3, 3))
        assert len(self.store.load_all()) == 2

    def test_a_failure_in_the_middle_undoes_everything(self):
        raises = self.assertRaises(sqlite3.IntegrityError)
        with raises, self.store._connect() as conn:
            conn.execute(
                "INSERT INTO entries (date_time, type, text) "
                "VALUES ('2020-01-01T00:00:00', 'text', 'first')"
            )
            conn.execute(
                "INSERT INTO entries (date_time, type, text) "
                "VALUES ('2020-01-01T00:00:00', 'video', 'second')"
            )
        assert self.store.load_all() == []

    def test_schema_version(self):
        with closing(sqlite3.connect(self.db_file)) as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION

    def test_newer_database_is_not_touched(self):
        with closing(sqlite3.connect(self.db_file)) as conn:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
            conn.commit()
        with self.assertRaises(StorageError):
            SqliteEntryStore(self.db_file)

    def test_a_file_that_is_no_database(self):
        other = os.path.join(self.folder, "not_a_db.sqlite")
        with open(other, "w") as f:
            f.write("This is not a database, just a text. " * 50)
        with self.assertRaises(StorageError):
            SqliteEntryStore(other)
        # The file was not changed
        with open(other) as f:
            assert f.read().startswith("This is not a database")

    def test_no_files_are_left_next_to_the_database(self):
        for k in range(3):
            self.store.save_entry(f"Entry {k}", datetime(2020, 1, 2, 3))
        assert os.listdir(self.folder) == ["diary.sqlite"]


class TestChangingEntries(TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="story_time_test_db_")
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.db_file = os.path.join(self.folder, "story_time.sqlite")
        self.store = SqliteEntryStore(self.db_file)
        self.first = self.store.save_entry("First", datetime(2020, 1, 1, 8))
        self.second = self.store.save_entry("Second", datetime(2020, 1, 2, 8))

    def texts(self):
        return [e.text for e in self.store.load_all()]

    def test_update(self):
        updated = self.store.update_entry(
            self.first.id, "Changed", datetime(2020, 1, 5, 9), "photo", "IMG_1.jpg"
        )
        assert updated == Entry(
            datetime(2020, 1, 5, 9), "photo", "Changed", "IMG_1.jpg", self.first.id
        )
        # It is where its new date puts it, and the other one did not change
        assert self.store.load_all() == [updated, self.second]

    def test_update_to_a_text_entry(self):
        photo = self.store.save_entry("P", datetime(2020, 2, 2), "photo", "a.jpg")
        updated = self.store.update_entry(photo.id, "P", photo.date_time)
        assert updated.type == "text" and updated.photo is None

    def test_update_checks_like_save(self):
        with self.assertRaises(ValueError):
            self.store.update_entry(self.first.id, "x", datetime(2020, 1, 1), "video")
        with self.assertRaises(AssertionError):
            self.store.update_entry(self.first.id, "x", datetime(2020, 1, 1), "photo")
        assert self.texts() == ["Second", "First"]

    def test_update_of_unknown_entry(self):
        with self.assertRaises(KeyError):
            self.store.update_entry(99, "x", datetime(2020, 1, 1))

    def test_same_time_entries_are_told_apart(self):
        same = datetime(2021, 5, 5, 5)
        one = self.store.save_entry("One", same)
        two = self.store.save_entry("Two", same)
        self.store.update_entry(two.id, "Two!", same)
        assert [(e.id, e.text) for e in self.store.load_all()[:2]] == [
            (one.id, "One"),
            (two.id, "Two!"),
        ]

    def test_trash_and_restore(self):
        self.store.trash_entry(self.first.id, datetime(2021, 1, 1))
        assert self.texts() == ["Second"]
        trash = self.store.load_trash()
        assert [e.text for e in trash] == ["First"]
        assert trash[0].deleted_at == datetime(2021, 1, 1)
        assert trash[0].id == self.first.id

        self.store.restore_entry(self.first.id)
        assert self.texts() == ["Second", "First"]
        assert self.store.load_trash() == []
        assert self.store.load_all()[1].deleted_at is None

    def test_the_last_deleted_is_first_in_the_trash(self):
        self.store.trash_entry(self.second.id, datetime(2021, 1, 1))
        self.store.trash_entry(self.first.id, datetime(2021, 1, 2))
        assert [e.text for e in self.store.load_trash()] == ["First", "Second"]

    def test_trash_and_restore_of_wrong_entries(self):
        with self.assertRaises(KeyError):
            self.store.trash_entry(99, datetime(2021, 1, 1))
        with self.assertRaises(KeyError):
            self.store.restore_entry(self.first.id)  # not in the trash
        self.store.trash_entry(self.first.id, datetime(2021, 1, 1))
        with self.assertRaises(KeyError):
            self.store.trash_entry(self.first.id, datetime(2021, 1, 2))
        assert self.store.load_trash()[0].deleted_at == datetime(2021, 1, 1)

    def test_delete_forever_only_takes_trashed_entries(self):
        self.store.trash_entry(self.first.id, datetime(2021, 1, 1))
        self.store.delete_forever([self.first.id, self.second.id, 99])
        assert self.store.load_trash() == []
        assert self.texts() == ["Second"]
        # Ids are not used again
        assert self.store.save_entry("Third", datetime(2020, 1, 3)).id > self.second.id

    def test_trash_is_kept_when_reopened(self):
        self.store.trash_entry(self.first.id, datetime(2021, 1, 1))
        again = SqliteEntryStore(self.db_file)
        assert [e.text for e in again.load_trash()] == ["First"]

    def test_database_of_the_first_version_is_migrated(self):
        old = os.path.join(self.folder, "old.sqlite")
        with closing(sqlite3.connect(old)) as conn:
            conn.executescript("""
                CREATE TABLE entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('text', 'photo')),
                    text TEXT NOT NULL,
                    photo TEXT
                );
                INSERT INTO entries (date_time, type, text)
                    VALUES ('2019-01-02T03:04:05', 'text', 'From before');
                PRAGMA user_version = 1;
                """)
        store = SqliteEntryStore(old)
        assert [e.text for e in store.load_all()] == ["From before"]
        store.trash_entry(1, datetime(2021, 1, 1))
        assert store.load_all() == [] and len(store.load_trash()) == 1
        with closing(sqlite3.connect(old)) as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
