import os
import shutil
from unittest import TestCase
import xml.etree.cElementTree as elTree

import wx

import lib
from lib.XML_write import (
    init_XML,
    insertXmlTextEntryElement,
    insertXmlPhotoEntryElement,
    getXMLAndFilename,
    saveEntryInXml,
    findLatestInDoc,
    getLastXMLEntry)
from lib import util
from tests.test_util import DATA_DIR

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
        insertXmlTextEntryElement(root, wx_dt, test_txt)
        assert elTree.ElementTree(root).find("entry").text == test_txt

    def test_photo_entry(self):
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        test_txt = "hoi"
        root = elTree.Element("root")
        insertXmlPhotoEntryElement(root, wx_dt, "file.test", test_txt)
        entry = elTree.ElementTree(root).find("entry")
        assert entry.find("text").text == test_txt
        assert entry.get("type") == "photo"

    def test_get_xml(self):
        lib.util.xml_folder = XML_DIR
        y = 2020
        tree, f = getXMLAndFilename(y)
        assert f == os.path.join(XML_DIR, f"{y}.xml")

    def test_entry_saving(self):
        lib.util.xml_folder = XML_DIR
        y = 2020
        wx_dt = wx.DateTime(2, 11, y, 5, 31)
        saveEntryInXml("Test", wx_dt, "text")
        saveEntryInXml("Test", wx_dt, "photo", "test_photo.jpg")
        saveEntryInXml("Test", wx_dt, "blah", "test_photo.jpg")
        tree, f = getXMLAndFilename(y)
        assert os.path.isfile(f)
        os.remove(f)
        pass

    def test_find_latest(self):
        el_tree = init_XML("Test", 2020)
        wx_dt_find = wx.DateTime(2, 11, 2020, 6, 31)
        doc = el_tree.getroot().find("doc")
        assert findLatestInDoc(el_tree, wx_dt_find, newer=False) is None
        n = 3
        for k in range(n):
            wx_dt = wx.DateTime(2, 11, 2020, k + 1, 31)
            insertXmlTextEntryElement(doc, wx_dt, f"Test_{k}")
        wx_dt_found, t = findLatestInDoc(el_tree, wx_dt_find, newer=False)
        assert wx.DateTime(2, 11, 2020, n, 31).IsEqualTo(wx_dt_found)

    def test_get_last_entry(self):
        lib.util.xml_folder = XML_DIR
        try:
            n = 3
            for k in range(n):
                wx_dt = wx.DateTime(2, 11, 2020 + k, 4, 31)
                saveEntryInXml(f"Test{k}", wx_dt, "text")
                wx_dt = wx.DateTime(2, 11, 2020 + k, 5, 31)
                saveEntryInXml(f"Test{k}_photo", wx_dt, "photo", f"test_photo_{k}.jpg")

            search_dt = wx.DateTime(2, 11, 2021, 5, 11)
            dt, ch_txt = getLastXMLEntry(search_dt, True)
            assert ch_txt.get("type") == "photo"
            dt, ch_txt = getLastXMLEntry(search_dt, False)
            assert ch_txt.text == "Test1"
            dt, ch_txt = getLastXMLEntry(wx.DateTime(2, 11, 2021, 1, 11), False)
            assert ch_txt.get("type") == "photo"
        finally:
            shutil.rmtree(XML_DIR)
    pass
