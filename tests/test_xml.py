import os
import xml.etree.ElementTree as elTree
from datetime import datetime
from unittest import TestCase

import wx

import story_time
import story_time.util
from story_time.XML_write import (
    Entry,
    filter_entries,
    find_closest_entry,
    find_closest_entry_in_tree,
    group_by_month,
    init_XML,
    insert_photo_entry,
    insert_text_entry,
    load_all_entries,
    load_XML,
    save_entry,
)
from tests.test_util import DATA_DIR, create_test_dirs, use_data_dir

XML_DIR = os.path.join(DATA_DIR, "XML")


class TestXML(TestCase):
    def test_init_XML(self):
        el_tree = init_XML("Test", 2020)
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
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        test_txt = "hoi"
        root = elTree.Element("root")
        insert_text_entry(root, wx_dt, test_txt)
        assert elTree.ElementTree(root).find("entry").text == test_txt

    def test_photo_entry(self):
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        test_txt = "hoi"
        root = elTree.Element("root")
        insert_photo_entry(root, wx_dt, "file.test", test_txt)
        entry = elTree.ElementTree(root).find("entry")
        assert entry.find("text").text == test_txt
        assert entry.get("type") == "photo"

    def test_get_xml(self):
        story_time.util.xml_folder = XML_DIR
        y = 2020
        tree, f = load_XML(y)
        assert f == os.path.join(XML_DIR, f"{y}.xml")

    def test_entry_saving(self):
        with create_test_dirs():
            story_time.util.xml_folder = XML_DIR
            y = 2020
            wx_dt = wx.DateTime(2, 11, y, 5, 31)

            save_entry("Test", wx_dt, "text")
            save_entry("Test", wx_dt, "photo", "test_photo.jpg")
            with self.assertRaises(ValueError):
                save_entry("Test", wx_dt, "blah", "test_photo.jpg")

            tree, f = load_XML(y)
            assert os.path.isfile(f)
            os.remove(f)

            with self.assertRaises(FileNotFoundError):
                load_XML(100000000, create=False)

    def test_find_latest(self):
        el_tree = init_XML("Test", 2020)
        wx_dt_find = wx.DateTime(2, 11, 2020, 6, 31)
        doc = el_tree.getroot().find("doc")
        assert find_closest_entry_in_tree(el_tree, wx_dt_find, newer=False) is None
        n = 3
        for k in range(n):
            wx_dt = wx.DateTime(2, 11, 2020, k + 1, 31)
            insert_text_entry(doc, wx_dt, f"Test_{k}")
        wx_dt_found, t = find_closest_entry_in_tree(el_tree, wx_dt_find, newer=False)
        assert wx.DateTime(2, 11, 2020, n, 31).IsEqualTo(wx_dt_found)

    def test_get_last_entry(self):
        with create_test_dirs():
            story_time.util.xml_folder = XML_DIR
            n = 3
            for k in range(n):
                wx_dt = wx.DateTime(2, 11, 2020 + k, 4, 31)
                save_entry(f"Test{k}", wx_dt, "text")
                wx_dt = wx.DateTime(2, 11, 2020 + k, 5, 31)
                save_entry(f"Test{k}_photo", wx_dt, "photo", f"test_photo_{k}.jpg")

            search_dt = wx.DateTime(2, 11, 2021, 5, 11)
            dt, ch_txt = find_closest_entry(search_dt, True)
            assert ch_txt.get("type") == "photo"
            dt, ch_txt = find_closest_entry(search_dt, False)
            assert ch_txt.text == "Test1"
            dt, ch_txt = find_closest_entry(wx.DateTime(2, 11, 2021, 1, 11), False)
            assert ch_txt.get("type") == "photo"
            dt, ch_txt = find_closest_entry(wx.DateTime(2, 11, 2021, 8, 11), True)
            assert ch_txt.get("type") == "text"
            assert find_closest_entry(wx.DateTime(2, 11, 3000, 1, 11), True) is None

    pass


class TestEntries(TestCase):
    @staticmethod
    def save(text, dt, photo=None):
        if photo is None:
            save_entry(text, dt)
        else:
            save_entry(text, dt, "photo", photo)

    def test_load_all_entries(self):
        with use_data_dir(DATA_DIR):
            with create_test_dirs():
                story_time.util.update_folder(DATA_DIR)
                assert load_all_entries() == []

                self.save("Old\nsecond line", wx.DateTime(5, 0, 2019, 8, 15, 30))
                self.save("Middle", wx.DateTime(2, 5, 2020, 10))
                self.save("Photo text", wx.DateTime(3, 5, 2020, 9), "IMG_1.jpg")
                self.save("New", wx.DateTime(1, 1, 2021, 23, 59, 59))

                entries = load_all_entries()

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
        with use_data_dir(DATA_DIR):
            with create_test_dirs():
                story_time.util.update_folder(DATA_DIR)
                save_entry("Valid", wx.DateTime(2, 5, 2020, 10))
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
                entries = load_all_entries()
        assert [e.text for e in entries] == ["Valid"]

    def test_filter_entries(self):
        e1 = Entry(datetime(2020, 1, 1), "text", "Walk by the Lake")
        e2 = Entry(datetime(2020, 1, 2), "photo", "Logo sketch", "a.jpg")
        entries = [e1, e2]
        assert filter_entries(entries, "") == entries
        assert filter_entries(entries, "   ") == entries
        assert filter_entries(entries, "lake") == [e1]
        assert filter_entries(entries, "SKETCH logo") == [e2]
        assert filter_entries(entries, "lake logo") == []

    def test_group_by_month(self):
        entries = [
            Entry(datetime(2020, 3, 5), "text", "a"),
            Entry(datetime(2020, 3, 1), "text", "b"),
            Entry(datetime(2020, 1, 9), "text", "c"),
            Entry(datetime(2019, 3, 9), "text", "d"),
        ]
        groups = group_by_month(entries)
        assert [k for k, _ in groups] == [(2020, 3), (2020, 1), (2019, 3)]
        assert [[e.text for e in g] for _, g in groups] == [["a", "b"], ["c"], ["d"]]
        assert group_by_month([]) == []
