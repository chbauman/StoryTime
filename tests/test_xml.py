import os
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest import TestCase

from story_time.xml_storage import (
    XmlEntryStore,
    init_xml,
    insert_photo_entry,
    insert_text_entry,
    load_xml,
)
from tests.helpers import DATA_DIR, create_test_dirs

XML_DIR = os.path.join(DATA_DIR, "XML")
STORE = XmlEntryStore(XML_DIR)


class TestXML(TestCase):
    def test_init_xml(self):
        el_tree = init_xml("Test", 2020)
        root = el_tree.getroot()
        doc = root.find("doc")
        assert doc is not None

        head = root.find("head")
        assert head is not None

        y = head.find("year").text
        assert int(y) == 2020

        t = head.find("text").text
        assert t == "Test"

    def test_text_entry(self):
        dt = datetime(2020, 12, 2, 5, 31)
        root = ET.Element("root")
        insert_text_entry(root, dt, "hoi")
        entry = ET.ElementTree(root).find("entry")
        assert entry.text == "hoi"
        assert entry.get("date_time") == "2020-12-02T05:31:00"
        assert entry.get("type") == "text"

    def test_photo_entry(self):
        dt = datetime(2020, 12, 2, 5, 31)
        root = ET.Element("root")
        insert_photo_entry(root, dt, "file.test", "hoi")
        entry = ET.ElementTree(root).find("entry")
        assert entry.find("text").text == "hoi"
        assert entry.find("photo").text == "file.test"
        assert entry.get("type") == "photo"
        assert entry.get("date_time") == "2020-12-02T05:31:00"

    def test_get_xml(self):
        _tree, f = load_xml(XML_DIR, 2020)
        assert f == os.path.join(XML_DIR, "2020.xml")

    def test_entry_saving(self):
        with create_test_dirs():
            y = 2020
            dt = datetime(y, 12, 2, 5, 31)

            STORE.save_entry("Test", dt, "text")
            STORE.save_entry("Test", dt, "photo", "test_photo.jpg")
            with self.assertRaises(ValueError):
                STORE.save_entry("Test", dt, "blah", "test_photo.jpg")
            with self.assertRaises(AssertionError):
                STORE.save_entry("Test", dt, "photo")

            _tree, f = load_xml(XML_DIR, y)
            assert os.path.isfile(f)
            # Same time, so the order of saving is kept
            assert [e.type for e in STORE.load_all()] == ["text", "photo"]
            os.remove(f)

            with self.assertRaises(FileNotFoundError):
                load_xml(XML_DIR, 100000000, create=False)

    def test_photo_path_is_reduced_to_the_file_name(self):
        with create_test_dirs():
            STORE.save_entry(
                "Text", datetime(2020, 1, 2, 3), "photo", "/some/where/a.jpg"
            )
            (entry,) = STORE.load_all()
        assert entry.photo == "a.jpg"


class TestEntries(TestCase):
    @staticmethod
    def save(text, dt, photo=None):
        if photo is None:
            STORE.save_entry(text, dt)
        else:
            STORE.save_entry(text, dt, "photo", photo)

    def test_load_all_entries(self):
        with create_test_dirs():
            assert STORE.load_all() == []

            self.save("Old\nsecond line", datetime(2019, 1, 5, 8, 15, 30))
            self.save("Middle", datetime(2020, 6, 2, 10))
            self.save("Photo text", datetime(2020, 6, 3, 9), "IMG_1.jpg")
            self.save("New", datetime(2021, 2, 1, 23, 59, 59))

            entries = STORE.load_all()

        # Newest first, over several years
        assert [e.text for e in entries] == [
            "New",
            "Photo text",
            "Middle",
            "Old\nsecond line",
        ]
        assert entries[0].date_time == datetime(2021, 2, 1, 23, 59, 59)
        assert entries[-1].date_time == datetime(2019, 1, 5, 8, 15, 30)
        assert entries[-1].type == "text" and entries[-1].photo is None
        assert entries[-1].first_line == "Old"
        photo = [e for e in entries if e.type == "photo"]
        assert len(photo) == 1
        assert photo[0].photo == "IMG_1.jpg" and photo[0].text == "Photo text"

    def test_invalid_files_and_entries_are_skipped(self):
        with create_test_dirs():
            STORE.save_entry("Valid", datetime(2020, 6, 2, 10))
            with open(os.path.join(XML_DIR, "2020.xml")) as f:
                xml = f.read()
            xml = xml.replace(
                "</doc>", '<entry date_time="no date" type="text">x</entry></doc>'
            )
            with open(os.path.join(XML_DIR, "2020.xml"), "w") as f:
                f.write(xml)
            with open(os.path.join(XML_DIR, "2019.xml"), "w") as f:
                f.write("not xml")
            with open(os.path.join(XML_DIR, "notes.txt"), "w") as f:
                f.write("ignored")
            entries = STORE.load_all()
        assert [e.text for e in entries] == ["Valid"]

    def test_without_xml_folder(self):
        assert XmlEntryStore(os.path.join(DATA_DIR, "does_not_exist")).load_all() == []
