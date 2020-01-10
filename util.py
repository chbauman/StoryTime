#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime
from shutil import copy2

import cv2
import wx
import wx.adv

# Paths to app code and temp folder
project_path = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(project_path, "Icons")
temp_folder = "tmp"

# Path to data (global variables)
# Initialized values should never be used
data_path = ""
img_folder = "fuck"
xml_folder = "fuck"


def update_folder(new_data_path: str) -> None:
    """Update global path variables if data folder is changed.
    """
    global data_path
    global img_folder
    global xml_folder

    data_path = new_data_path
    img_folder = os.path.join(new_data_path, "Img")
    xml_folder = os.path.join(new_data_path, "XML")


def rep_newlines_with_space(string: str) -> str:
    """Removes newlines and replaces them with spaces.

    Also reduces double spaces to single spaces.
    """
    return string.replace("\n", " ").replace("  ", " ")


def create_xml_and_img_folder(base_folder: str) -> None:
    """Create a folder for the XML and the image files.
    """
    xml_pth = os.path.join(base_folder, "XML")
    if not os.path.isdir(xml_pth):
        os.mkdir(xml_pth)
    img_pth = os.path.join(base_folder, "Img")
    if not os.path.isdir(img_pth):
        os.mkdir(img_pth)
    return


def get_info_from_file(ask: bool = True):
    """Read the info file and get necessary information

    Args:
        ask: Whether to ask for a directory.

    Returns:

    """
    if not os.path.exists("Info.txt"):
        with open("Info.txt", "w") as f:
            f.write("NoDirectorySpecified")
    with open("Info.txt") as file:
        data = file.readlines()
        print(data)

        if data != [] and os.path.isdir(data[0]):
            fol_path = data[0]
            # TODO: More checks or create dirs?
            create_xml_and_img_folder(fol_path)
            return fol_path
        elif ask:
            cdDiag = wx.DirDialog(None, "Choose directory to store Imgs and Text data.", "",
                                  wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
            cdDiag.ShowModal()
            files_path = cdDiag.GetPath()
            create_xml_and_img_folder(files_path)
            return files_path
    return None


def write_folder_to_file() -> None:
    """Write the current working directory to file Info.txt
    """
    with open("Info.txt", "w") as f:
        f.write(data_path)


def scale_bitmap(bitmap: wx.Bitmap, width, height) -> wx.Bitmap:
    """Rescales a bitmap to a given size.

    Converting it to image, rescaling and converting it back.
    """
    image = bitmap.ConvertToImage()
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.Bitmap(image)
    return result


class ChangeDateDialog(wx.Dialog):
    """Date and Time picker dialog"""
    cal: wx.adv.CalendarCtrl
    timePicker: wx.adv.TimePickerCtrl

    def __init__(self, *args, **kw):
        super(ChangeDateDialog, self).__init__(*args, **kw)

        self.dt = wx.DateTime.Now()
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle("Change Date of entry")

    def InitUI(self):
        pnl = wx.Panel(self)
        vertical_box = wx.BoxSizer(wx.VERTICAL)

        # Calendar and Time Picker
        sb = wx.StaticBox(pnl, label='Select Date and Time')
        sbs = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        self.cal = wx.adv.CalendarCtrl(pnl)
        sbs.Add(self.cal, flag=wx.ALL, border=5)
        self.timePicker = wx.adv.TimePickerCtrl(pnl)
        sbs.Add(self.timePicker, flag=wx.ALL, border=5)
        pnl.SetSizer(sbs)

        # Buttons
        h_box_2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Ok')
        cancelButton = wx.Button(self, label='Cancel')
        h_box_2.Add(okButton)
        h_box_2.Add(cancelButton, flag=wx.LEFT, border=5)

        vertical_box.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vertical_box.Add(h_box_2, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(vertical_box)

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


class PhotoWithSameDateExistsDialog(wx.Dialog):
    """Dialog that pops up if you want to save an image, but
    there exists an image with the same associated time."""

    v_box: wx.BoxSizer

    img: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    next_button: wx.Button
    prev_button: wx.Button

    def __init__(self, file_list, parent=None, title="Image with same date already exists"):
        super(PhotoWithSameDateExistsDialog, self).__init__(parent, title=title)

        self.fileList = file_list
        self.chosenImgInd = None
        self.shownImgInd = 0
        self.maxInd = len(file_list)
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle(title)

    def InitUI(self):

        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self.bmp_shown = self.get_img_at_ind(0)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        self.v_box.Add(self.img, proportion=0, flag=wx.ALL, border=5)
        self.img.Show()

        # Buttons
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        selectButton = wx.Button(self, label='Select')
        newButton = wx.Button(self, label='New')

        h_box.Add(selectButton)

        if self.maxInd > 1:  # No next / previous if there is only one
            self.next_button = wx.Button(self, label='Next')
            self.prev_button = wx.Button(self, label='Previous')
            self.prev_button.Disable()
            h_box.Add(self.prev_button)
            h_box.Add(self.next_button)
            self.next_button.Bind(wx.EVT_BUTTON, self.OnNext)
            self.prev_button.Bind(wx.EVT_BUTTON, self.OnPrev)

        h_box.Add(newButton, flag=wx.LEFT, border=5)
        self.v_box.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        self.v_box.Add(h_box, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(self.v_box)

        selectButton.Bind(wx.EVT_BUTTON, self.OnSelect)
        newButton.Bind(wx.EVT_BUTTON, self.OnNew)

    def get_img_at_ind(self, ind):
        return getImageToShow(os.path.join(img_folder, self.fileList[ind]), size=100, border=5)

    def updateImg(self):
        ind = self.shownImgInd
        img_to_show = self.get_img_at_ind(ind)
        self.img.SetBitmap(img_to_show)

    def OnNext(self, e):
        print("Next Image")
        self.shownImgInd += 1
        if self.shownImgInd == self.maxInd - 1:
            self.next_button.Disable()
        if self.shownImgInd == 1:
            self.prev_button.Enable()
        self.updateImg()
        print("next img")

    def OnPrev(self, e):
        self.shownImgInd -= 1
        if self.shownImgInd == 0:
            self.prev_button.Disable()
        if self.shownImgInd == self.maxInd - 2:
            self.next_button.Enable()
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
        self.chosenImgInd = -1  # This means new
        self.Close()


def datetime_to_wx_datetime(date: datetime) -> wx.DateTime:
    """Converts a python datetime to a wx.DateTime.
    """
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    return wx.DateTime(day, month - 1, year, hour, date.minute, date.second)


def get_file_modified_wx_dt(curr_file: str) -> wx.DateTime:
    """Read the date modified time of a file, convert it to wx.DateTime
    and return it.
    """
    modify_time = os.path.getmtime(curr_file)
    return datetime_to_wx_datetime(datetime.fromtimestamp(modify_time))


def pad_int_str(int_to_pad: int, n: int = 2) -> str:
    """Converts an integer to a string, padding with leading zeros
    to get n characters. Intended for date and time formatting.
    """
    base = str(int_to_pad)
    for k in range(n - 1):
        if int_to_pad < 10 ** (k + 1):
            base = "0" + base
    return base


def get_img_name_from_time(wx_dt: wx.DateTime) -> str:
    """Gives the image basename from the wx.DateTime.
    """
    name = "IMG_" + pad_int_str(wx_dt.GetYear(), 4) + pad_int_str(wx_dt.GetMonth() + 1) + pad_int_str(wx_dt.GetDay())
    name = name + "_" + pad_int_str(wx_dt.GetHour()) + pad_int_str(wx_dt.GetMinute()) + pad_int_str(wx_dt.GetSecond())
    return name


def extract_date_from_image_name(img_file: str):
    """Extracts the date information from the image name.

    Tries to extract the date and optionally the time.
    If extracted date is not valid or there is no date
    contained in the name, returns None.
    """
    p, filename = os.path.split(img_file)
    # Extract all numbers from string
    nums = re.findall(r'\d+', filename)
    num_nums = len(nums)
    if num_nums < 1:
        print("No Date extracted!")
        return None
    date = int(nums[0])
    # Year must be greater than 1
    if date < 10000:
        print("Invalid date.")
        return None
    year = date // 10000
    rem = date - year * 10000
    month = (rem // 100)
    day = rem - month * 100
    hour = mins = sec = 0

    # Extract time
    if len(nums) > 1:
        num_curr = int(nums[1])
        len_num = len(nums[1])
        if len_num == 6:
            sec = num_curr % 100
            num_curr = num_curr // 100
        if len_num == 4 or len_num == 6:
            mins = num_curr % 100
            hour = num_curr // 100

    # Check if date is valid
    try:
        wx_dt = wx.DateTime(day, month - 1, year, hour, mins, sec)
        if not wx_dt.IsValid():
            return None
        return wx_dt
    except Exception as e:
        print(f"Exception: {e} happened :(")
        return None


def get_time_from_file(img_file):
    """Tries to extract the date from a filename.

    If there is none, returns the modified time
    of the file as wx.DateTime.
    """
    name_date = extract_date_from_image_name(img_file)
    if name_date is None:
        name_date = get_file_modified_wx_dt(img_file)
    return name_date


def findAllImgsWithSameDate(imgs_folder, imgName):
    """
    Finds all files starting with string "imgName" 
    in folder "img_folder".
    """
    res = []
    for f in os.listdir(imgs_folder):
        if f.startswith(imgName):
            res.append(f)
    return res


def getNewName(imgName, sameDateFileList, ext):
    """
    Chooses a new filename that is not in the list and
    contains the imgName in the beginning by appending an 
    int to the filename separated by an underscore.
    """
    for k in range(10000):
        new_name = imgName + "_" + str(k) + ext
        try:
            found = sameDateFileList.index(new_name)
        except:
            return imgName + "_" + str(k)

    # If there are already more than 10000 images, gives up.
    print("ERROR: Way too many fucking images.")
    return None


def copyImgFileToImgs(lf):
    """
    Copy an image to the Img folder, if there exists one with 
    the same date and time, a dialog pops up
    to let the user select if he wants to add 
    text to an existing image or save the image
    If he doesn't decide, returns None
    """
    # Get date of image and find all images with same date
    imgDate = get_time_from_file(lf)
    imgName = get_img_name_from_time(imgDate)
    sameDateFileList = findAllImgsWithSameDate(img_folder, imgName)
    print(sameDateFileList)

    # Get image type
    _, file_extension = os.path.splitext(lf)

    # Check if file with same datetime already exists
    if len(sameDateFileList) > 0:
        # Let the user look at the images and decide if he wants
        # to add the text to an already existing one instead of
        # adding the image in preview to the images.
        phDiag = PhotoWithSameDateExistsDialog(sameDateFileList)
        phDiag.ShowModal()
        ind = phDiag.chosenImgInd
        phDiag.Destroy()
        if ind is None:
            # No decision, abort
            return None
        if ind == -1:
            # Add image in preview
            imgName = getNewName(imgName, sameDateFileList, file_extension)
        else:
            # Add text to existing image
            imgName = sameDateFileList[ind]
            return os.path.join(img_folder, imgName)

    # Add file extension and copy image to project
    imgName = imgName + file_extension
    copied_file_name = os.path.join(img_folder, imgName)
    copy2(lf, copied_file_name)
    return copied_file_name


def chooseImgTextMethod(lf, imgDT=None):
    _, file_extension = os.path.splitext(lf)
    if imgDT is None:
        imgDate = get_time_from_file(lf)
    else:
        imgDate = imgDT
    imgName = get_img_name_from_time(imgDate)
    useExisting = False

    # TODO: Check if already in correct folder
    if os.path.normpath(os.path.dirname(lf)) == os.path.normpath(img_folder):
        print("Already in right folder.")
        return lf, imgDate, True

    # Check if file already exists
    sameDateFileList = findAllImgsWithSameDate(img_folder, imgName)
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
            return os.path.join(img_folder, new_name), imgDate, useExisting
        imgName = new_name
        phDiag.Destroy()

    imgName = imgName + file_extension
    copied_file_name = os.path.join(img_folder, imgName)
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


def mkrid_if_not_exists(dir_name):
    """
    Creates the given directory recursively.
    """
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return


class FileDrop(wx.FileDropTarget):
    """Drop Target to drop images to be added.
    """

    origImgDate = None

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

        # Get date and set image
        self.origImgDate = get_time_from_file(curr_file)
        self.frame.set_img_with_date(curr_file, self.origImgDate)
        self.loadedFile = curr_file

        return True


def formDateTime(date_time):
    """Format the given datetime in a string.
    """
    str_out = str(wx.DateTime.GetWeekDayName(date_time.GetWeekDay())) + ", "
    str_out += str(date_time.GetDay()) + ". "
    str_out += str(date_time.GetMonth() + 1) + ". "
    str_out += str(date_time.GetYear()) + ", Time: "
    str_out += str(date_time.GetHour()) + ":"
    str_out += str(date_time.GetMinute()) + ":"
    str_out += str(date_time.GetSecond())
    return str_out


# Assuming quadratic size
def getImageToShow(filename, size=180, border=5):
    bor_2 = 2 * border
    wxBmp = wx.Bitmap(filename)
    image = wxBmp.ConvertToImage()
    imgSize = image.GetSize()
    max_size = imgSize[0] if imgSize[0] > imgSize[1] else imgSize[1]
    fac = size / max_size
    s_diff_half = abs(imgSize[0] - imgSize[1]) * fac / 2
    image.Rescale(fac * imgSize[0], fac * imgSize[1], wx.IMAGE_QUALITY_HIGH)
    img_sz = wx.Size(size + bor_2, size + bor_2)
    image.Resize(img_sz, wx.Point(border, border + s_diff_half), 0, 0, 0)
    result = wx.Bitmap(image)
    return result


# Panel that shows the content recorded by the webcam
class ShowCapture(wx.Panel):
    def __init__(self, parent, capture, fps=25):

        # Capture first frame to get size
        self.capture = capture
        ret, frame = self.capture.read()
        height, width = frame.shape[:2]
        self.h_by_w = height / width
        self.win_size = (300, int(self.h_by_w * 300))

        wx.Panel.__init__(self, parent, wx.ID_ANY, (0, 0), self.win_size)
        parent.SetSize(self.win_size)

        self.h, self.w = self.win_size
        frame = cv2.cvtColor(cv2.resize(frame, self.win_size), cv2.COLOR_BGR2RGB)
        self.bmp = wx.Bitmap.FromBuffer(self.h, self.w, frame)

        self.timer = wx.Timer(self)
        self.timer.Start(1000. / fps)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)

    def getCurrFrame(self):
        ret, frame = self.capture.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, event):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(cv2.resize(frame, self.win_size), cv2.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(frame)
            self.Refresh()


# Dialog lets you look at the taken picture and decide if you want to take a new one or keep it
class AcceptPhoto(wx.Dialog):

    def __init__(self, parent=None, img=None, title="Accept photo?"):
        super(AcceptPhoto, self).__init__(parent, title=title)

        self.taken_img = img
        self.InitUI()
        self.SetSize((400, 400))
        self.SetTitle(title)
        self.accepted = False

    def InitUI(self):
        pnl = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        height, width, c = self.taken_img.shape
        self.orig_img = self.taken_img
        height, width = (300, int(height / width * 300))
        new_size = width, height
        new_size = height, width
        self.taken_img = cv2.resize(self.taken_img, new_size)
        bmp = wx.Bitmap.FromBuffer(height, width, self.taken_img.tobytes())
        bmp = wx.StaticBitmap(self, -1, bmp, size=new_size)
        self.vbox.Add(bmp, proportion=0, flag=wx.ALL, border=5)

        # Buttons        
        shootButton = wx.Button(self, label='Accept')
        cancelButton = wx.Button(self, label='Throw')
        shootButton.Bind(wx.EVT_BUTTON, self.OnTakePic)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)

        # Layout
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(shootButton)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)

        self.vbox.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        self.vbox.Add(hbox2, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(self.vbox)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    # Captures the current frame
    def OnTakePic(self, e):
        print("Accepting img")
        self.accepted = True
        self.Cleanup()

    # Release the video capture
    def Cleanup(self):
        self.Destroy()
        pass

    def OnClose(self, e):
        print("Cancelled Accept Dialog")
        self.Cleanup()


# Dialog lets you take a picture with the webcam
class SelfieDialog(wx.Dialog):

    def __init__(self, parent=None, title="Let me take a fucking selfie."):
        super(SelfieDialog, self).__init__(parent, title=title)

        self.InitUI()
        self.SetSize((400, 400))
        self.SetTitle(title)
        self.taken_img = None
        self.dt_taken = None

    def InitUI(self):
        pnl = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self.capture = cv2.VideoCapture(0)
        self.imgCap = ShowCapture(self, self.capture)
        self.vbox.Add(self.imgCap, proportion=0, flag=wx.ALL, border=5)
        self.imgCap.Show()

        # Buttons        
        shootButton = wx.Button(self, label='Shoot')
        cancelButton = wx.Button(self, label='Cancel')
        shootButton.Bind(wx.EVT_BUTTON, self.OnTakePic)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)

        # Layout
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(shootButton)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)

        self.vbox.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        self.vbox.Add(hbox2, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(self.vbox)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnTakePic(self, e):
        """
        Captures the current frame and
        shows the Dialog that lets the user accept the photo or decide
        to take another one.
        """
        accept_diag = AcceptPhoto(None, img=self.imgCap.getCurrFrame())
        accept_diag.ShowModal()
        if accept_diag.accepted:
            self.taken_img = accept_diag.orig_img
            self.Cleanup()
        accept_diag.Destroy()

    def Cleanup(self):
        """
        Release the video capture.
        """
        self.capture.release()
        cv2.destroyAllWindows()
        self.Destroy()

    def OnClose(self, e):
        print("Cancelled Selfie Dialog")
        self.Cleanup()
