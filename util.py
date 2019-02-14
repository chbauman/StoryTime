#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import wx
import re
import wx.adv
from shutil import copy2
from PIL import Image
from datetime import datetime

# Path to folder containing the XML and the Img folder
data_path = "" #os.path.join(os.path.dirname(os.path.realpath(__file__)), "Teescht")

# Path to app code
proj_path = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(proj_path, "Icons")

#imgs_folder = os.path.join(data_path, "Img")
#xml_folder = os.path.join(data_path, "XML")
imgs_folder = "fuck"
xml_folder = "fuck"

# Update global path variables if folder is changed
def updateFolder(new_data_path):
    global data_path
    global imgs_folder
    global xml_folder
    
    data_path = new_data_path
    imgs_folder = os.path.join(new_data_path, "Img")
    xml_folder = os.path.join(new_data_path, "XML")

# Removes newlines and replaces them with space
def repNewlWithSpace(strng):
    return strng.replace("\n", " ").replace("  ", " ")


# Create a folder for the XML and the Image files
def createXMLandImgFolderIfNotExist(base_folder):
    xml_pth = os.path.join(base_folder, "XML")
    if not os.path.isdir(xml_pth):
        os.mkdir(xml_pth)
    img_pth = os.path.join(base_folder, "Img")
    if not os.path.isdir(img_pth):
        os.mkdir(img_pth)
    return

# Read the info file and get necessary information
def getInfoFromFile(ask = True):
    if not os.path.exists("Info.txt"):
        with open("Info.txt", "w") as f:
            f.write("NoDirectorySpecified")
    with open("Info.txt") as file:
        data = file.readlines() 
        print(data)
        
        if data != [] and os.path.isdir(data[0]):
            fol_path = data[0]
            # TODO: More checks or create dirs?
            createXMLandImgFolderIfNotExist(fol_path)
            return fol_path
        elif ask:
            cdDiag = wx.DirDialog(None, "Choose directory to store Imgs and Text data.", "",
                    wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
            cdDiag.ShowModal()
            files_path = cdDiag.GetPath()
            createXMLandImgFolderIfNotExist(files_path)
            return files_path
    return None

# Write the current working directory to file
def writeFolderToFile():
    with open("Info.txt", "w") as f:
        f.write(data_path)
    return

# Scale a bitmap to a given size
def scale_bitmap(bitmap, width, height):
    image = bitmap.ConvertToImage()
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.Bitmap(image)
    return result

# Date and Time picker dialog
class ChangeDateDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        super(ChangeDateDialog, self).__init__(*args, **kw)

        self.dt = wx.DateTime.Now()
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle("Change Date of entry")

    def InitUI(self):

        pnl = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Calendar and Time Picker
        sb = wx.StaticBox(pnl, label='Select Date and Time')
        sbs = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        self.cal = wx.adv.CalendarCtrl(pnl)
        sbs.Add(self.cal, flag=wx.ALL, border = 5)
        self.timePicker = wx.adv.TimePickerCtrl(pnl)
        sbs.Add(self.timePicker, flag=wx.ALL, border = 5)
        pnl.SetSizer(sbs)

        # Buttons
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Ok')
        cancelButton = wx.Button(self, label='Cancel')
        hbox2.Add(okButton)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)

        vbox.Add(pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

        self.SetSizer(vbox)

        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)


    def OnClose(self, e):

        print("Closed Change Date Dialog")
        self.Close()
    
    def OnOK(self, e):
        timeTuple = self.timePicker.GetTime()
        self.dt = self.cal.GetDate()
        self.dt.SetHour(timeTuple[0])
        self.dt.SetMinute(timeTuple[1])
        self.dt.SetSecond(timeTuple[2])
        print(self.dt)
        self.Close()  

# Dialog that pops up if you want to save an image, but there exists an image with the same associated time
class PhotoWithSameDateExistsDialog(wx.Dialog):

    def __init__(self, fileList, parent = None, title = "Image with same date already exists"):
        super(PhotoWithSameDateExistsDialog, self).__init__(parent, title = title)

        self.fileList = fileList
        self.chosenImgInd = None
        self.shownImgInd = 0
        self.maxInd = len(fileList)
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle(title)

    def InitUI(self):

        pnl = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self.bmp_shown = self.getImgatInd(0)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        self.vbox.Add(self.img, proportion=0, flag=wx.ALL, border=5)
        self.img.Show()

        # Buttons
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        selectButton = wx.Button(self, label='Select')
        newButton = wx.Button(self, label='New')

        hbox2.Add(selectButton)

        if self.maxInd > 1: # No next / previous if there is only one
            self.nextButton = wx.Button(self, label='Next')
            self.prevButton = wx.Button(self, label='Previous')
            self.prevButton.Disable()
            hbox2.Add(self.prevButton)
            hbox2.Add(self.nextButton)
            self.nextButton.Bind(wx.EVT_BUTTON, self.OnNext)
            self.prevButton.Bind(wx.EVT_BUTTON, self.OnPrev)

        hbox2.Add(newButton, flag=wx.LEFT, border=5)
        self.vbox.Add(pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        self.vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

        self.SetSizer(self.vbox)

        selectButton.Bind(wx.EVT_BUTTON, self.OnSelect)
        newButton.Bind(wx.EVT_BUTTON, self.OnNew)
    

    def getImgatInd(self, ind):
        return getImageToShow(os.path.join(imgs_folder , self.fileList[ind]), size = 100, border = 5)
    
    def updateImg(self):
        ind = self.shownImgInd
        img_to_show = self.getImgatInd(ind)
        self.img.SetBitmap(img_to_show)

    def OnNext(self, e):
        print("Next Image")
        self.shownImgInd += 1
        if self.shownImgInd == self.maxInd - 1:
            self.nextButton.Disable()
        if self.shownImgInd == 1:
            self.prevButton.Enable()
        self.updateImg()
        print("next img")

    def OnPrev(self, e):
        self.shownImgInd -= 1
        if self.shownImgInd == 0:
            self.prevButton.Disable()
        if self.shownImgInd == self.maxInd - 2:
            self.nextButton.Enable()
        self.updateImg()
        print("Prev img")

    def OnSelect(self, e):
        self.chosenImgInd = self.shownImgInd
        self.Close()
        pass

    def OnClose(self, e):
        print("Closed Change Date Dialog")
        self.Close()
    
    def OnNew(self, e):
        self.chosenImgInd = -1 # This means new
        self.Close()  

# Converts a python datetime to a wx.DateTime
def pydate2wxdate(date):
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    return wx.DateTime(day, month-1, year, hour, date.minute, date.second)

def getWXDTFileModified(curr_file):
    return pydate2wxdate(datetime.fromtimestamp(os.path.getmtime(curr_file)))

# Converts an integer to a string, padding with leading zeros to get n characters
def pat0ToStr(integ, n = 2):
    base = str(integ)
    for k in range(n-1):
        if integ < 10**(k+1):
            base = "0" + base
    return base

# Gives the image basename from the wx.DateTime
def getImgBNameFromModTime(wxdt):
    name = "IMG_" + pat0ToStr(wxdt.GetYear(), 4) + pat0ToStr(wxdt.GetMonth() + 1) + pat0ToStr(wxdt.GetDay())
    name = name + "_" + pat0ToStr(wxdt.GetHour()) + pat0ToStr(wxdt.GetMinute()) + pat0ToStr(wxdt.GetSecond())
    return name

# Extracts the date information from the image name
def extractDateFromImageName(img_file):
    p, filename = os.path.split(img_file)
    nums = re.findall(r'\d+', filename)
    num_nums = len(nums)
    if num_nums < 1:
        print("No Date extracted!")
        return None
    date = int(nums[0])
    if date < 10000:
        print("Invalid date.")
        return None
    year = date // 10000
    rem = date - year * 10000
    month = (rem // 100)
    day = rem - month * 100
    hour = min = sec = 0
    if len(nums) > 1:
        num_curr = int(nums[1])
        len_num = len(nums[1])
        if len_num == 6:
            sec = num_curr % 100
            num_curr = num_curr // 100
        if len_num == 4 or len_num == 6:
            min = num_curr % 100
            hour = num_curr // 100
    try:
        wxdt = wx.DateTime(day, month - 1, year, hour, min, sec)
        if not wxdt.IsValid():
            return None
        return wxdt
    except:
        return None
    return None

# Tries to extract the date from a filename, if there is none, returns the modified time, as wx.DateTime
def getFilenameOrModifiedDate(img_file):
    name_date = extractDateFromImageName(img_file)
    if name_date is None:
        name_date = getWXDTFileModified(img_file)
    return name_date

# Finds all files starting with string "imgName" in folder "imgs_folder"
def findAllImgsWithSameDate(imgs_folder, imgName):
    res = []
    for f in os.listdir(imgs_folder):
        if f.startswith(imgName):

            res.append(f)
    return res

# Chooses a new filename that is not in the list and contains the imgName in the beginning
def getNewName(imgName, sameDateFileList, ext):
    for k in range(10000):
        new_name = imgName + "_" + str(k) + ext
        try:
            found = sameDateFileList.index(new_name)
        except:
            return imgName + "_" + str(k)
    print("ERROR: Way too many fucking images.")
    return None

# Copy an image to the Img folder, if there exists one with the same date and time, a dialog pops up
# to let the user select if he wants to add text to an existing image or save the image
# If he doesn't decide, returns None
def copyImgFileToImgs(lf):
     _, file_extension = os.path.splitext(lf)
     imgDate = getFilenameOrModifiedDate(lf)
     imgName = getImgBNameFromModTime(imgDate)

     print(findAllImgsWithSameDate(imgs_folder, imgName))

     # TODO: Check if already in correct folder

     # Check if file already exists
     sameDateFileList = findAllImgsWithSameDate(imgs_folder, imgName)
     if len(sameDateFileList) > 0:
         print("File already exists, overwriting it. TODO: Dialog")
         phDiag = PhotoWithSameDateExistsDialog(sameDateFileList)
         phDiag.ShowModal()
         ind = phDiag.chosenImgInd
         if ind is None:
             return None
         if ind == -1:
             new_name = getNewName(imgName, sameDateFileList, file_extension)
         else:
             # do not copy
             new_name = sameDateFileList[ind]
             return os.path.join(imgs_folder, new_name)
         imgName = new_name
         phDiag.Destroy()
         

     imgName = imgName + file_extension
     copied_file_name = os.path.join(imgs_folder, imgName)
     copy2(lf, copied_file_name)
     return copied_file_name

def chooseImgTextMethod(lf, imgDT = None):
    _, file_extension = os.path.splitext(lf)
    if imgDT is None:
        imgDate = getFilenameOrModifiedDate(lf)
    else:
        imgDate = imgDT
    imgName = getImgBNameFromModTime(imgDate)
    useExisting = False

    # TODO: Check if already in correct folder
    if os.path.normpath(os.path.dirname(lf)) == os.path.normpath(imgs_folder):
        print("Already in right folder.")
        return lf, imgDate, True

    # Check if file already exists
    sameDateFileList = findAllImgsWithSameDate(imgs_folder, imgName)
    if len(sameDateFileList) > 0:
         print("File already exists, overwriting it. TODO: Dialog")
         phDiag = PhotoWithSameDateExistsDialog(sameDateFileList)
         phDiag.ShowModal()
         ind = phDiag.chosenImgInd
         if ind is None:
             return None
         if ind == -1:
             new_name = getNewName(imgName, sameDateFileList, file_extension)
         else:
             # do not copy
             new_name = sameDateFileList[ind]
             useExisting = True
             return os.path.join(imgs_folder, new_name), imgDate, useExisting
         imgName = new_name
         phDiag.Destroy()
         
    imgName = imgName + file_extension
    copied_file_name = os.path.join(imgs_folder, imgName)
    return copied_file_name, imgDate, useExisting

def copyImgFileToImgsIfNotExistFull(old_f_name, date):
    copied_file_name, imgDate, useExisting = chooseImgTextMethod(old_f_name, date)
    if not useExisting:
        copy2(old_f_name, copied_file_name)
    return copied_file_name

def copyImgFileToImgsIfNotExist(old_f_name, useExisting, new_fname):
    if not useExisting:
        copy2(old_f_name, new_fname)
        return new_fname
    return old_f_name

class FileDrop(wx.FileDropTarget):

    def __init__(self, window, frame):

        wx.FileDropTarget.__init__(self)
        self.window = window
        self.frame = frame
        self.loadedFile = None
        self.newFileName = None

    def OnDropFiles(self, x, y, filenames):

        if len(filenames) > 1:
            print("Can only process one file at a time.")
        curr_file = filenames[0]
        _, ext = os.path.splitext(curr_file)
        ext = ext[1:].lower()
        if ext != "jpg" and ext != "jpeg" and ext != "png" and ext != "bmp":
            print("ERROR: Unsupported fucking file type!")
            return False

        self.origImgDate = getFilenameOrModifiedDate(curr_file)

        self.frame.updateDate(self.origImgDate)
        self.frame.imgLoaded = True
        self.loadedFile = curr_file
        self.frame.setImg(curr_file)

        return True

def formDateTime(dateTime):
    strOut = str(wx.DateTime.GetWeekDayName(dateTime.GetWeekDay())) + ", " 
    strOut += str(dateTime.GetDay()) + ". " 
    strOut += str(dateTime.GetMonth() + 1) + ". " 
    strOut += str(dateTime.GetYear()) + ", Time: "
    strOut += str(dateTime.GetHour()) + ":"
    strOut += str(dateTime.GetMinute()) + ":"
    strOut += str(dateTime.GetSecond())
    return strOut

# Assuming quadratic size
def getImageToShow(filename, size = 180, border = 5):

    bor_2 = 2 * border
    wxBmp = wx.Bitmap(filename)
    image = wxBmp.ConvertToImage()
    imgSize = image.GetSize()
    max_size = imgSize[0] if imgSize[0] > imgSize[1] else imgSize[1]
    fac = size / max_size
    s_diff_half = abs(imgSize[0] - imgSize[1]) * fac / 2
    image.Rescale(fac * imgSize[0], fac * imgSize[1], wx.IMAGE_QUALITY_HIGH)
    image.Resize(wx.Size(size + bor_2, size + bor_2), wx.Point(border, border + s_diff_half), 0, 0, 0)
    result = wx.Bitmap(image)
    return result

