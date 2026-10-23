#!/usr/bin/env python3
"""This module contains the XML reading and writing utilities.

All the text is stored in an XML file and the images are referenced
in the file.
"""

import os
import re
import xml.etree.ElementTree as elTree
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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


def insert_text_entry(doc: elTree.Element, date_time: datetime, text: str) -> None:
    """Inserts a text entry into the XML element tree.

    Args:
        doc: The doc element. Entry will be inserted as child.
        date_time: The DateTime of the entry.
        text: The text of the entry.
    """
    dt = date_time.isoformat(timespec="seconds")
    elTree.SubElement(doc, "entry", date_time=dt, type="text").text = text


def insert_photo_entry(
    doc: elTree.Element, date_time: datetime, img_filename: str, text: str
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
        doc, "entry", date_time=date_time.isoformat(timespec="seconds"), type="photo"
    )
    elTree.SubElement(ent, "text").text = text
    elTree.SubElement(ent, "photo").text = img_filename


def load_XML(
    xml_folder: str, year: int, create: bool = True
) -> tuple[elTree.ElementTree, str]:
    """Loads an existing XML file and returns the Element tree.

    If it does not exist, a new element tree is initializes.

    Args:
        xml_folder: The folder with the XML files.
        year: The year specifying the XML file.
        create: Whether to return a new tree if file not found.

    Returns:
        The element tree and the filename.
    """
    yearStr = str(year)
    xml_file = os.path.join(xml_folder, f"{yearStr}.xml")
    if os.path.exists(xml_file):
        tree = elTree.parse(xml_file)
    elif create:
        tree = init_XML("Das isch es Johr " + yearStr + ".", year)
    else:
        raise FileNotFoundError("File not found and create == False")
    return tree, xml_file


@dataclass
class Entry:
    """An entry of the diary."""

    date_time: datetime
    type: str  #: Either "text" or "photo".
    text: str
    photo: Optional[str] = None  #: For photo entries the file name in the Img folder.

    @property
    def first_line(self) -> str:
        """The first non-empty line of the text."""
        for line in self.text.splitlines():
            if line.strip():
                return line.strip()
        return ""


def _entry_from_element(element: elTree.Element) -> Optional[Entry]:
    """Converts an entry element, returns None if it is not valid."""
    try:
        date_time = datetime.fromisoformat(element.get("date_time", ""))
    except ValueError:
        return None
    if element.get("type") == "photo":
        text = element.findtext("text") or ""
        return Entry(date_time, "photo", text, element.findtext("photo"))
    return Entry(date_time, "text", element.text or "")


class EntryStore:
    """The entries of the diary, stored in one XML file per year in a folder."""

    def __init__(self, xml_folder: str) -> None:
        self.xml_folder = xml_folder

    def save_entry(
        self,
        comm: str,
        date_time: datetime,
        entry_type: str = "text",
        img_filename: Optional[str] = None,
    ) -> None:
        """Reads the XML file and adds an entry element with the specified content.

        Then saves the tree back to the file.

        Args:
            comm: The text for the entry.
            date_time: The date and time of the entry.
            entry_type: The type of the entry, either "text" or "photo".
            img_filename: For a photo the image file, only its name is stored.
        """
        year = date_time.year
        tree, xml_file = load_XML(self.xml_folder, year)

        doc = tree.getroot().find("doc")
        assert doc is not None, f"No doc found in XML of year {year}."
        if entry_type == "text":
            insert_text_entry(doc, date_time, comm)
        elif entry_type == "photo":
            assert img_filename is not None, "Need to specify image filename!"
            insert_photo_entry(doc, date_time, os.path.basename(img_filename), comm)
        else:
            raise ValueError(f"Entry of type: {entry_type} is not supported!")
        tree.write(xml_file)

    def load_all(self) -> list[Entry]:
        """Loads the entries of all XML files in the folder, newest first.

        Files and entries that are not valid are skipped.
        """
        entries: list[Entry] = []
        if not os.path.isdir(self.xml_folder):
            return entries
        for name in sorted(os.listdir(self.xml_folder)):
            if not re.fullmatch(r"\d+\.xml", name):
                continue
            try:
                tree = elTree.parse(os.path.join(self.xml_folder, name))
            except (elTree.ParseError, OSError):
                continue
            doc = tree.getroot().find("doc")
            if doc is None:
                continue
            for element in doc.findall("entry"):
                entry = _entry_from_element(element)
                if entry is not None:
                    entries.append(entry)
        entries.sort(key=lambda e: e.date_time, reverse=True)
        return entries


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
