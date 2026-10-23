import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from unittest import TestCase

from story_time.entries import Entry
from story_time.folders import DataFolder
from story_time.sqlite_storage import SqliteEntryStore
from story_time.storage import export_xml, open_store
from story_time.xml_storage import XmlEntryStore


def checksums(folder: str) -> dict:
    """The checksums of all files in a folder."""
    result = {}
    for name in sorted(os.listdir(folder)):
        with open(os.path.join(folder, name), "rb") as f:
            result[name] = hashlib.sha256(f.read()).hexdigest()
    return result


class StorageTestCase(TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="story_time_test_storage_")
        self.addCleanup(shutil.rmtree, self.base, True)
        self.folder = DataFolder(self.base)
        self.folder.create()

    def write_legacy(self):
        """Writes entries in XML files like older versions did."""
        xml = XmlEntryStore(self.folder.xml_folder)
        xml.save_entry("Old\nsecond line", datetime(2019, 1, 5, 8, 15, 30))
        xml.save_entry("Middle", datetime(2020, 6, 2, 10))
        xml.save_entry("Photo text", datetime(2020, 6, 3, 9), "photo", "IMG_1.jpg")
        xml.save_entry("Same time A", datetime(2021, 2, 1, 23, 59, 59))
        xml.save_entry("Same time B", datetime(2021, 2, 1, 23, 59, 59))
        xml.save_entry("Umlauts \u00e4\u00f6\u00fc", datetime(2021, 3, 1, 12))


class TestOpenStore(StorageTestCase):
    def test_new_diary_is_empty(self):
        store = open_store(self.folder)
        assert store.load_all() == []
        assert os.path.isfile(self.folder.db_file)
        # No XML folder is made for a new diary
        assert not os.path.exists(self.folder.xml_folder)

    def test_xml_entries_are_taken_over(self):
        self.write_legacy()
        expected = XmlEntryStore(self.folder.xml_folder).load_all()
        entries = open_store(self.folder).load_all()

        assert len(entries) == 6
        # The same entries in the same order, now with ids
        assert [(e.date_time, e.type, e.text, e.photo) for e in entries] == [
            (e.date_time, e.type, e.text, e.photo) for e in expected
        ]
        assert all(e.id is not None for e in entries)
        assert [e.text for e in entries][:3] == [
            "Umlauts \u00e4\u00f6\u00fc",
            "Same time A",
            "Same time B",
        ]

    def test_the_xml_files_stay_as_a_backup(self):
        self.write_legacy()
        before = checksums(self.folder.xml_folder)
        open_store(self.folder)
        open_store(self.folder)
        assert checksums(self.folder.xml_folder) == before
        assert sorted(before) == ["2019.xml", "2020.xml", "2021.xml"]

    def test_taking_over_happens_only_once(self):
        self.write_legacy()
        store = open_store(self.folder)
        store.save_entry("New one", datetime(2022, 1, 1))
        # Later entries in the XML files, e.g. from an older version, are not mixed in
        XmlEntryStore(self.folder.xml_folder).save_entry("Late", datetime(2022, 5, 5))

        texts = [e.text for e in open_store(self.folder).load_all()]
        assert "New one" in texts and "Late" not in texts
        assert len(texts) == 7

    def test_no_incomplete_database_is_left(self):
        self.write_legacy()
        open_store(self.folder)
        assert sorted(os.listdir(self.base)) == ["Img", "XML", "story_time.sqlite"]

    def test_an_interrupted_import_is_started_again(self):
        self.write_legacy()
        with open(self.folder.db_file + ".importing", "w") as f:
            f.write("rest of an import that was interrupted")
        assert len(open_store(self.folder).load_all()) == 6
        assert not os.path.exists(self.folder.db_file + ".importing")

    def test_a_broken_xml_file_does_not_stop_the_import(self):
        self.write_legacy()
        with open(os.path.join(self.folder.xml_folder, "2018.xml"), "w") as f:
            f.write("not xml")
        assert len(open_store(self.folder).load_all()) == 6

    def test_existing_database_is_opened_as_it_is(self):
        SqliteEntryStore(self.folder.db_file).save_entry("Mine", datetime(2020, 1, 1))
        self.write_legacy()  # Would be taken over, if there were no database
        entries = open_store(self.folder).load_all()
        assert [e.text for e in entries] == ["Mine"]

    def test_xml_folder_without_entries(self):
        os.makedirs(self.folder.xml_folder)
        assert open_store(self.folder).load_all() == []


class TestExportXml(StorageTestCase):
    def entries(self):
        return [
            Entry(datetime(2021, 2, 1, 23, 59, 59), "text", "Same A", None, 4),
            Entry(datetime(2021, 2, 1, 23, 59, 59), "text", "Same B", None, 5),
            Entry(datetime(2020, 6, 3, 9), "photo", "Photo text", "IMG_1.jpg", 3),
            Entry(
                datetime(2020, 6, 2, 10),
                "text",
                "Line 1\n\nLine 3 \u00e4\u20ac",
                None,
                2,
            ),
            Entry(datetime(2019, 1, 5, 8, 15, 30), "text", "Old", None, 1),
        ]

    def test_export_and_read_again(self):
        target = os.path.join(self.base, "exported")
        paths = export_xml(self.entries(), target)
        assert sorted(os.path.basename(p) for p in paths) == [
            "2019.xml",
            "2020.xml",
            "2021.xml",
        ]
        read = XmlEntryStore(target).load_all()
        without_ids = [
            Entry(e.date_time, e.type, e.text, e.photo) for e in self.entries()
        ]
        assert [(e.date_time, e.type, e.text, e.photo) for e in read] == [
            (e.date_time, e.type, e.text, e.photo) for e in without_ids
        ]

    def test_round_trip_through_the_database(self):
        self.write_legacy()
        entries = open_store(self.folder).load_all()
        target = os.path.join(self.base, "exported")
        export_xml(entries, target)
        again = XmlEntryStore(target).load_all()
        assert [(e.date_time, e.type, e.text, e.photo) for e in again] == [
            (e.date_time, e.type, e.text, e.photo) for e in entries
        ]

    def test_existing_files_are_not_overwritten(self):
        self.write_legacy()
        before = checksums(self.folder.xml_folder)
        with self.assertRaises(FileExistsError):
            export_xml(self.entries(), self.folder.xml_folder)
        assert checksums(self.folder.xml_folder) == before

    def test_nothing_is_written_if_one_of_the_files_exists(self):
        target = os.path.join(self.base, "exported")
        os.makedirs(target)
        with open(os.path.join(target, "2020.xml"), "w") as f:
            f.write("mine")
        with self.assertRaises(FileExistsError):
            export_xml(self.entries(), target)
        assert sorted(os.listdir(target)) == ["2020.xml"]

    def test_overwrite(self):
        target = os.path.join(self.base, "exported")
        export_xml(self.entries(), target)
        export_xml(self.entries()[:1], target, overwrite=True)
        assert next(e.text for e in XmlEntryStore(target).load_all()) == "Same A"

    def test_no_temporary_files_are_left(self):
        target = os.path.join(self.base, "exported")
        export_xml(self.entries(), target)
        assert all(name.endswith(".xml") for name in os.listdir(target))

    def test_nothing_to_export(self):
        target = os.path.join(self.base, "exported")
        assert export_xml([], target) == []
