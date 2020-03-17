#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module contains the XML reading and writing utilities.

All the text is stored in an XML file and the images are referenced
in the file.
"""
import os
import xml.etree.cElementTree as elTree
from shutil import copy2

import wx

from lib import util
from lib.util import get_time_from_file, img_folder, get_img_name_from_time


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


def insertXmlTextEntryElement(doc, date_time, text):
    elTree.SubElement(doc, "entry", date_time=date_time.FormatISOCombined(),
                      type="text").text = text


def insertXmlPhotoEntryElement(doc, date_time, img_filename, text) -> None:
    """Inserts a photo entry element as a child of the elTree doc.

    Args:
        doc:
        date_time:
        img_filename:
        text:

    Returns:

    """
    if img_filename is None:
        print("ERROR: No fucking filename provided for inserting into XML.")
        return
    # TODO: Check if file exists
    ent = elTree.SubElement(doc, "entry", date_time=date_time.FormatISOCombined(), type="photo")
    elTree.SubElement(ent, "text").text = text
    elTree.SubElement(ent, "photo").text = img_filename


def getXMLAndFilename(year, create=True):
    yearStr = str(year)
    xml_file = os.path.join(util.xml_folder, yearStr + ".xml")
    if os.path.exists(xml_file):
        tree = elTree.parse(xml_file)
    elif create:
        tree = init_XML("Das isch es Johr " + yearStr + ".", year)
    else:
        return None
    return tree, xml_file


def saveEntryInXml(comm, date_time, entry_type: str = "text", img_filename: str = None):
    """Reads the XML file and adds an entry element with the specified content

    Args:
        comm:
        date_time:
        entry_type:
        img_filename:

    Returns:

    """
    year = date_time.GetYear()
    tree, xml_file = getXMLAndFilename(year)

    doc = tree.getroot().find("doc")
    if entry_type == "text":
        insertXmlTextEntryElement(doc, date_time, comm)
    elif entry_type == "photo":
        insertXmlPhotoEntryElement(doc, date_time, os.path.basename(img_filename), comm)
    else:
        print("WTF are you doing??")
    tree.write(xml_file)


def find_next_older_xml_file(year, newer=False):
    """Finds the most recent XML file before year 'year'.

    If there is none return None, else the found year and the tree of the XML.
    if newer == True, then it finds the next newer one

    Args:
        year:
        newer:

    Returns:

    """
    closest_year = -100000
    if newer:
        closest_year = 100000
    for f in os.listdir(util.xml_folder):
        y = int(f.split(".")[0])
        if not newer and year > y > closest_year:
            closest_year = y
        if newer and year < y < closest_year:
            closest_year = y
    if abs(closest_year) == 100000:
        return None
    return closest_year, getXMLAndFilename(closest_year, False)[0]


def findLatestInDoc(tree, date_time, newer=False):
    """Finds most recent date_time entry in doc.

    If there is no earlier entry than 'date_time' returns None
    if newer == True, then it finds the next newer one

    Args:
        tree:
        date_time:
        newer:

    Returns:

    """
    doc = tree.getroot().find("doc")
    temp = wx.DateTime(1, 1, 0)
    if newer:
        temp = wx.DateTime(1, 1, 100000)
    curr_child = None
    for child in doc:
        if child.get("type") != "text":
            continue
        wxDT = wx.DateTime()
        wxDT.ParseISOCombined(child.get("date_time"))
        if (not newer and temp < wxDT < date_time) or (newer and temp > wxDT > date_time):
            temp = wxDT
            curr_child = child
    if abs(temp.GetYear() - 50000) == 50000:
        return None
    return temp, curr_child


def getLastXMLEntry(dt, newer=False):
    """Get the latest entry before 'dt', if any

    Args:
        dt:
        newer:

    Returns:

    """
    curr_year = dt.GetYear()
    tree = getXMLAndFilename(curr_year, False)
    date_child = None
    if tree is not None:
        tree = tree[0]
        date_child = findLatestInDoc(tree, dt, newer)
        if date_child is None:
            tree = None
    if tree is None:
        date_child = None
        while date_child is None:
            res = find_next_older_xml_file(curr_year, newer)
            if res is None:
                return None
            tree = res[1]
            curr_year = res[0]
            date_child = findLatestInDoc(tree, dt, newer)

    assert date_child is not None
    date, child = date_child
    return date, child.text


def convertFromTxt(txt_file):
    """Takes the text document written by the old program and adds all the entries to the XML

    Args:
        txt_file:

    Returns:

    """
    with open(txt_file, 'r', encoding='utf-8-sig') as f:
        data = f.read()
        entry_list = data.split("\n\nDate: ")
        if entry_list[0][:6] == "Date: ":
            entry_list[0] = entry_list[0][6:]
        for k in entry_list:
            date, text = k.split("\n\n")
            wxDT = wx.DateTime(int(date[8:10]), int(date[5:7]) - 1, int(date[:4]), int(date[17:19]), int(date[20:22]))
            saveEntryInXml(text, wxDT)
        return


def addImgs(base_folder) -> None:
    """Takes the text document written by the old program and adds all the entries to the XML.

    Args:
        base_folder:

    Returns:

    """
    imgFolder = os.path.join(base_folder, "Img")
    imgDescFolder = os.path.join(base_folder, "ImgDesc")
    for f in os.listdir(imgFolder):
        base = os.path.basename(f)
        f_name, file_ext = os.path.splitext(base)
        full_img_filename = os.path.join(imgFolder, f)
        img_desc_f_name = os.path.join(imgDescFolder, f_name + ".txt")

        dateTime = get_time_from_file(full_img_filename)
        text = "No Desc."
        if os.path.exists(img_desc_f_name):
            with open(img_desc_f_name, 'r', encoding='utf-8-sig') as f_2:
                text = f_2.read()
        b_name_date = get_img_name_from_time(dateTime)
        ct = 0
        while True:
            new_img_name = os.path.join(img_folder, b_name_date + "_" + str(ct) + file_ext)
            ct += 1
            if not os.path.exists(new_img_name):
                break

        copy2(full_img_filename, new_img_name)
        saveEntryInXml(text, dateTime, "photo", new_img_name)
