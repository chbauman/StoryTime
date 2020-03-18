#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module contains the XML reading and writing utilities.

All the text is stored in an XML file and the images are referenced
in the file.
"""
import os
import xml.etree.cElementTree as elTree
from typing import Tuple, Optional

import wx

from lib import util


def init_XML(comm: str, year: int) -> elTree.ElementTree:
    """Initializes an XML document for a new year.

    Args:
        comm: A comment for the beginning of the year.
        year: The year of the document.

    Returns:
        XML element tree.
    """
    root = elTree.Element("root")
    head = elTree.SubElement(root, "head")
    elTree.SubElement(head, "year").text = str(year)
    elTree.SubElement(head, "text").text = comm
    elTree.SubElement(root, "doc")
    return elTree.ElementTree(root)


def insert_text_entry(doc: elTree.Element, date_time: wx.DateTime, text: str) -> None:
    """Inserts a text entry into the XML element tree.

    Args:
        doc: The doc element. Entry will be inserted as child.
        date_time: The DateTime of the entry.
        text: The text of the entry.
    """
    dt = date_time.FormatISOCombined()
    elTree.SubElement(doc, "entry", date_time=dt, type="text").text = text


def insert_photo_entry(
    doc: elTree.Element, date_time: wx.DateTime, img_filename: str, text: str
) -> None:
    """Inserts a photo entry element as a child of the elTree doc.

    Args:
        doc: The doc element. Entry will be inserted as child.
        date_time: The DateTime of the entry.
        img_filename: The file name referring to the image.
        text: The text of the entry.
    """
    # TODO: Check if file exists?
    ent = elTree.SubElement(
        doc, "entry", date_time=date_time.FormatISOCombined(), type="photo"
    )
    elTree.SubElement(ent, "text").text = text
    elTree.SubElement(ent, "photo").text = img_filename


def load_XML(year: int, create: bool = True) -> Tuple[elTree.ElementTree, str]:
    """Loads an existing XML file and returns the Element tree.

    If it does not exist, a new element tree is initializes.

    Args:
        year: The year specifying the XML file.
        create: Whether to return a new tree if file not found.

    Returns:
        The element tree and the filename.
    """
    yearStr = str(year)
    xml_file = os.path.join(util.xml_folder, f"{yearStr}.xml")
    if os.path.exists(xml_file):
        tree = elTree.parse(xml_file)
    elif create:
        tree = init_XML("Das isch es Johr " + yearStr + ".", year)
    else:
        raise FileNotFoundError("File not found and create == False")
    return tree, xml_file


def save_entry(
    comm: str,
    date_time: wx.DateTime,
    entry_type: str = "text",
    img_filename: str = None,
) -> None:
    """Reads the XML file and adds an entry element with the specified content.

    Then saves the tree back to the file.

    Args:
        comm: The text for the entry.
        date_time: The DateTime of the entry.
        entry_type: The type of the entry, either "text" or "photo".
        img_filename:
    """
    year = date_time.GetYear()
    tree, xml_file = load_XML(year)

    doc = tree.getroot().find("doc")
    if entry_type == "text":
        insert_text_entry(doc, date_time, comm)
    elif entry_type == "photo":
        insert_photo_entry(doc, date_time, os.path.basename(img_filename), comm)
    else:
        raise ValueError(f"Entry of type: {entry_type} is not supported!")
    tree.write(xml_file)


def find_next_xml_file(
    year: int, newer: bool = False
) -> Optional[Tuple[int, elTree.ElementTree]]:
    """Finds the most recent XML file before year 'year'.

    If there is none, returns None, otherwise, the found year and the tree of the XML
    is returned.
    If `newer` == True, then it finds the next newer one

    Args:
        year:
        newer:

    Returns:
        The year of the closest entry and the element tree of the
        closes XML file.
    """
    closest_year = 100000 if newer else -100000
    for f in os.listdir(util.xml_folder):
        y = int(f.split(".")[0])
        if not newer and year > y > closest_year:
            closest_year = y
        if newer and year < y < closest_year:
            closest_year = y
    if abs(closest_year) == 100000:
        return None
    return closest_year, load_XML(closest_year, False)[0]


def find_closest_entry_in_tree(
    tree: elTree.ElementTree, date_time: wx.DateTime, newer: bool = False
) -> Optional[Tuple[wx.DateTime, elTree.Element]]:
    """Finds entry closest to `date_time` in doc.

    If there is no earlier entry than 'date_time' returns None.
    If newer == True, then it finds the next newer one

    Args:
        tree: The element tree to search.
        date_time: The search date and time.
        newer: Whether to find the closest newer entry.

    Returns:
        The date of the found entry and the entry element.
    """
    doc = tree.getroot().find("doc")
    temp = wx.DateTime(1, 1, 100000 if newer else 0)
    curr_child = None
    for child in doc:
        wxDT = wx.DateTime()
        wxDT.ParseISOCombined(child.get("date_time"))
        if (not newer and temp < wxDT < date_time) or (
            newer and temp > wxDT > date_time
        ):
            temp = wxDT
            curr_child = child
    if abs(temp.GetYear() - 50000) == 50000:
        return None
    return temp, curr_child


def find_closest_entry(
    dt: wx.DateTime, newer: bool = False
) -> Optional[Tuple[wx.DateTime, elTree.Element]]:
    """Finds the latest entry before 'dt', if any.

    Searches all available XML files.

    Args:
        dt: The search date and time.
        newer: Whether to find the closest newer entry.

    Returns:
        The date of the found entry and the entry element.
        If there is no next entry, None is returned.
    """
    curr_year = dt.GetYear()

    # Load XML file with specified year
    tree = None
    try:
        tree = load_XML(curr_year, False)
    except FileNotFoundError:
        pass
    date_child = None
    if tree is not None:
        tree = tree[0]
        date_child = find_closest_entry_in_tree(tree, dt, newer)
        if date_child is None:
            tree = None

    # Entry not found yet, search next XML files
    if tree is None:
        date_child = None
        while date_child is None:
            res = find_next_xml_file(curr_year, newer)
            if res is None:
                # No next file found, return None
                return None
            tree = res[1]
            curr_year = res[0]
            date_child = find_closest_entry_in_tree(tree, dt, newer)

    # Return
    assert date_child is not None, f"Terrible bug is happening!"
    date, child = date_child
    return date, child
