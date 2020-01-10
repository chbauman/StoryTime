#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import wx
import xml.etree.cElementTree as ET

import util
from util import *

util.xml_folder


def init_XML(comm, year):
    root = ET.Element("root")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "year").text = str(year)
    ET.SubElement(head, "text").text = comm
    doc = ET.SubElement(root, "doc")
    return ET.ElementTree(root)


def insertXmlTextEntryElement(doc, dateTime, text):
    ent = ET.SubElement(doc, "entry", date_time=dateTime.FormatISOCombined(), type="text").text = text


# Inserts a photo entry element as a child of the ET doc
def insertXmlPhotoEntryElement(doc, dateTime, img_filename, text):
    if (img_filename == None):
        print("ERROR: No fucking filename provided for inserting into XML.")
        return
    # TODO: Check if file exists
    ent = ET.SubElement(doc, "entry", date_time=dateTime.FormatISOCombined(), type="photo")
    txt = ET.SubElement(ent, "text").text = text
    pht = ET.SubElement(ent, "photo").text = img_filename


def getXMLAndFilename(year, create=True):
    yearStr = str(year)
    xml_file = os.path.join(util.xml_folder, yearStr + ".xml")
    if os.path.exists(xml_file):
        tree = ET.parse(xml_file)
    elif create:
        tree = init_XML("Das isch es Johr " + yearStr + ".", year)
    else:
        return None
    return tree, xml_file


# Reads the XML file and adds an entry element with the specified content
def saveEntryInXml(comm, dateTime, type="text", img_filename=None):
    year = dateTime.GetYear()
    tree, xml_file = getXMLAndFilename(year)

    doc = tree.getroot().find("doc")
    if type == "text":
        insertXmlTextEntryElement(doc, dateTime, comm)
    elif type == "photo":
        insertXmlPhotoEntryElement(doc, dateTime, os.path.basename(img_filename), comm)
    else:
        print("WTF are you doing??")
    tree.write(xml_file)


# Finds the most recent XML file before year 'year', if there is 
# none return None, else the found year and the tree of the XML.
# if newer == True, then it finds the next newer one
def findNextOlderXMLfile(year, newer=False):
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


# Finds most recent date_time entry in doc, if there is no earlier entry than 'dateTime' returns None
# if newer == True, then it finds the next newer one
def findLatestInDoc(tree, dateTime, newer=False):
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
        if (not newer and wxDT > temp and wxDT < dateTime) or (newer and wxDT < temp and wxDT > dateTime):
            temp = wxDT
            curr_child = child
    if abs(temp.GetYear() - 50000) == 50000:
        return None
    return temp, curr_child


# Get the latest entry before 'dt', if any
def getLastXMLEntry(dt, newer=False):
    curr_year = dt.GetYear()
    tree = getXMLAndFilename(curr_year, False)
    if tree is not None:
        tree = tree[0]
        date_child = findLatestInDoc(tree, dt, newer)
        if date_child == None:
            tree = None
    if tree is None:
        date_child = None
        while date_child is None:
            res = findNextOlderXMLfile(curr_year, newer)
            if res is None:
                return None
            tree = res[1]
            curr_year = res[0]
            date_child = findLatestInDoc(tree, dt, newer)

    date, child = date_child
    return date, child.text


# Takes the text document written by the old program and adds all the entries to the XML
def convertFromTxt(txt_file):
    with open(txt_file, 'r', encoding='utf-8-sig') as myfile:
        data = myfile.read()
        entry_list = data.split("\n\nDate: ")
        if entry_list[0][:6] == "Date: ":
            entry_list[0] = entry_list[0][6:]
        for k in entry_list:
            date, text = k.split("\n\n")
            wxDT = wx.DateTime(int(date[8:10]), int(date[5:7]) - 1, int(date[:4]), int(date[17:19]), int(date[20:22]))
            saveEntryInXml(text, wxDT)
        return
    print("Fucking file could not be read!!")
    return


# Takes the text document written by the old program and adds all the entries to the XML
def addImgs(baseFolder):
    imgFolder = os.path.join(baseFolder, "Img")
    imgDescFolder = os.path.join(baseFolder, "ImgDesc")
    for f in os.listdir(imgFolder):
        base = os.path.basename(f)
        f_name, file_ext = os.path.splitext(base)
        full_img_filename = os.path.join(imgFolder, f)
        img_desc_f_name = os.path.join(imgDescFolder, f_name + ".txt")

        dateTime = getFilenameOrModifiedDate(full_img_filename)
        text = "No Desc."
        if os.path.exists(img_desc_f_name):
            with open(img_desc_f_name, 'r', encoding='utf-8-sig') as myfile:
                text = myfile.read()
        b_name_date = getImgBNameFromModTime(dateTime)
        ct = 0
        while True:
            new_img_name = os.path.join(util.imgs_folder, b_name_date + "_" + str(ct) + file_ext)
            ct += 1
            if not os.path.exists(new_img_name):
                break

        copy2(full_img_filename, new_img_name)
        saveEntryInXml(text, dateTime, "photo", new_img_name)

    return
