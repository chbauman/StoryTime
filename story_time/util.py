#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Some general utility functions.

Includes os stuff, dialogs for the main frame,
datetime conversions...
"""

import os
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import List, Callable, Sequence, Optional

import cv2
import wx
import wx.adv
from pkg_resources import resource_filename

import story_time

# Paths to app code and temp folder
project_path = Path(os.path.dirname(os.path.realpath(__file__))).parent
icon_path = os.path.join(project_path, "story_time/Icons")
temp_folder = os.path.join(
    project_path, "tmp"
)  #: Temporary folder to store images temporarily.
info_file = resource_filename(__name__, f"Info.txt")

# Path to data (global variables)
# Initialized values should never be used
# Also they should not be imported from the module since they change
# when initializing the app.
data_path = ""  #: The folder containing the image and the xml folder.
img_folder = "if/you/see/this/its/a/bug"  #: The folder where the images are stored.
xml_folder = (
    "if/you/see/this/its/a/bug"  #: The folder where the xml documents are stored.
)

# Set colors
# dark_green = wx.Colour(1, 92, 68)
green = wx.Colour(0, 143, 105)
light_green = wx.Colour(169, 245, 213)
very_light_green = wx.Colour(212, 252, 235)

header_col = light_green
but_bg_col = green
text_bg_col = very_light_green

# Fonts
header_f_info = wx.FontInfo(12).Bold().Family(wx.FONTFAMILY_SWISS)
button_f_info = wx.FontInfo(12).Family(wx.FONTFAMILY_SWISS).Bold()


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
    """Create a folder for the XML and the image files in `base_folder`.
    """
    xml_pth = os.path.join(base_folder, "XML")
    if not os.path.isdir(xml_pth):
        os.mkdir(xml_pth)
    img_pth = os.path.join(base_folder, "Img")
    if not os.path.isdir(img_pth):
        os.mkdir(img_pth)
    return


def check_date_time(
    y: int, mon: int, d: int, h: int = 0, minute: int = 0, sec: int = 0
) -> bool:
    """Checks if the provided date and time is valid."""
    try:
        datetime(y, mon, d, h, minute, sec)
    except ValueError:
        return False
    return True


def ask_for_dir(_fun: Callable = None, show: bool = True):
    """Ask the user to select a directory."""
    dial_text = "Choose directory to store Imgs and Text data."
    flags = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
    cdDiag = wx.DirDialog(None, dial_text, "", flags)
    if _fun is not None:
        _fun(cdDiag)
    cdDiag.ShowModal() if show else None
    return cdDiag.GetPath()


def get_info_from_file(ask: bool = True, _fun: Callable = None) -> Optional[str]:
    """Read the info file and get necessary information

    Also creates sub-folders if they do not exist.

    Args:
        ask: Whether to ask for a directory.
        _fun: Function to call when dialog pops up. For testing.

    Returns:
        Contents of the file.
    """
    if not os.path.exists(info_file):
        with open(info_file, "w") as f:
            f.write("NoDirectorySpecified")
    with open(info_file) as file:
        data = file.readlines()
        if data != [] and os.path.isdir(data[0]):
            fol_path = data[0]
            create_xml_and_img_folder(fol_path)
            return fol_path
        elif ask:
            files_path = story_time.util.ask_for_dir(_fun)
            create_xml_and_img_folder(files_path)
            return files_path


def write_folder_to_file() -> None:
    """Write the current working directory to file `info_file`.
    """
    with open(info_file, "w") as f:
        f.write(data_path)


def scale_bitmap(bitmap: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
    """Rescales a bitmap to a given size.

    Converting it to image, rescaling and converting it back.
    """
    image = bitmap.ConvertToImage()
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.Bitmap(image)
    return result


class ButtonDialogBase(wx.Dialog):
    """Base class for a dialog with a button."""

    v_box: wx.BoxSizer

    def setup_v_box(self, h_box, h_button, pnl):
        h_box.Add(h_button, flag=wx.LEFT, border=5)
        self.v_box.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        self.v_box.Add(h_box, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)
        self.SetSizer(self.v_box)
        self.SetBackgroundColour(text_bg_col)


class TwoButtonDialogBase(ButtonDialogBase):
    """Base class for a dialog with at least two buttons."""

    def setup(
        self,
        pnl: wx.Panel,
        shoot_label: str,
        cancel_label: str,
        shoot_fun: Callable = None,
        cancel_fun: Callable = None,
    ):
        """Layout setup, to be called in self.InitUI."""
        if shoot_fun is None:
            shoot_fun = self.OnTakePic
        if cancel_fun is None:
            cancel_fun = self.OnClose

        # Buttons
        shootButton = wx.Button(self, label=shoot_label)
        # shootButton.SetBackgroundColour(but_bg_col)
        shootButton.Bind(wx.EVT_BUTTON, shoot_fun)
        cancelButton = wx.Button(self, label=cancel_label)
        cancelButton.Bind(wx.EVT_BUTTON, cancel_fun)
        # cancelButton.SetBackgroundColour(but_bg_col)
        shootButton.SetFont(wx.Font(button_f_info))
        cancelButton.SetFont(wx.Font(button_f_info))

        # Layout
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        h_box.Add(shootButton)

        self.setup_v_box(h_box, cancelButton, pnl)

    def OnTakePic(self, e):
        pass

    def OnClose(self, e):
        pass


class CustomMessageDialog(TwoButtonDialogBase):

    okay: bool = False

    def __init__(
        self,
        message: str = None,
        title: str = "Message",
        *args,
        cancel_only: bool = False,
        ok_label: str = "Ok",
        cancel_label: str = "Cancel",
        **kw,
    ):
        super().__init__(*args, **kw)
        self.SetTitle(title)
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        if message is not None:
            stMsg = wx.StaticText(self, -1, message)
            # stMsg.SetBackgroundColour(green)
            self.v_box.Add(stMsg, 1, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(self.v_box)

        if cancel_only:
            h_box = wx.BoxSizer(wx.HORIZONTAL)
            cancel_butt = wx.Button(self, label=cancel_label)
            cancel_butt.Bind(wx.EVT_BUTTON, self.OnOK)
            cancel_butt.SetFont(wx.Font(button_f_info))
            self.setup_v_box(h_box, cancel_butt, pnl)
        else:
            self.setup(pnl, ok_label, cancel_label, self.OnOK, self.OnClose)

    def OnOK(self, _):
        print("Okay")
        self.okay = True
        self.Close()

    def OnClose(self, _):
        print("cancel")
        self.Close()


class ChangeDateDialog(TwoButtonDialogBase):
    """Date and Time picker dialog"""

    dt: wx.DateTime
    cal: wx.adv.CalendarCtrl
    timePicker: wx.adv.TimePickerCtrl

    def __init__(self, *args, **kw):
        super(ChangeDateDialog, self).__init__(*args, **kw)

        self.dt = wx.DateTime.Now()
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle("Change Date of entry")

    def InitUI(self) -> None:
        pnl = wx.Panel(self)

        # Calendar and Time Picker
        sb = wx.StaticBox(pnl, label="Select Date and Time")
        sbs = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        self.cal = wx.adv.CalendarCtrl(pnl)
        sbs.Add(self.cal, flag=wx.ALL, border=5)
        self.timePicker = wx.adv.TimePickerCtrl(pnl)
        sbs.Add(self.timePicker, flag=wx.ALL, border=5)
        pnl.SetSizer(sbs)

        # Add buttons
        self.v_box = wx.BoxSizer(wx.VERTICAL)
        self.setup(pnl, "Ok", "Cancel", self.OnOK, self.OnClose)

    def OnClose(self, e) -> None:
        print("Closed Change Date Dialog")
        self.Close()

    def OnOK(self, _) -> None:
        """Sets `self.dt` to the current time."""
        timeTuple = self.timePicker.GetTime()
        self.dt = self.cal.GetDate()
        self.dt.SetHour(timeTuple[0])
        self.dt.SetMinute(timeTuple[1])
        self.dt.SetSecond(timeTuple[2])
        print(self.dt)
        self.Close()


class PhotoWithSameDateExistsDialog(ButtonDialogBase):
    """Dialog that pops up if you want to save an image, but
    there exists an image with the same associated time."""

    img: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    next_button: wx.Button
    prev_button: wx.Button

    def __init__(
        self,
        file_list: Sequence,
        parent=None,
        title: str = "Image with same date already exists",
    ):
        super(PhotoWithSameDateExistsDialog, self).__init__(parent, title=title)

        self.file_list = file_list
        self.chosenImgInd = None
        self.shownImgInd = 0
        self.n_files = len(file_list)
        self.InitUI()
        self.SetSize((400, 300))
        self.SetTitle(title)

    def InitUI(self) -> None:

        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self.bmp_shown = self.get_img_at_ind(0)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        self.v_box.Add(self.img, proportion=0, flag=wx.ALL, border=5)
        self.img.Show()

        # Buttons
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        selectButton = wx.Button(self, label="Select")
        newButton = wx.Button(self, label="New")

        h_box.Add(selectButton)

        if self.n_files > 1:  # No next / previous if there is only one
            self.next_button = wx.Button(self, label="Next")
            self.prev_button = wx.Button(self, label="Previous")
            self.prev_button.Disable()
            h_box.Add(self.prev_button)
            h_box.Add(self.next_button)
            self.next_button.Bind(wx.EVT_BUTTON, self.OnNext)
            self.prev_button.Bind(wx.EVT_BUTTON, self.OnPrev)

        self.setup_v_box(h_box, newButton, pnl)
        selectButton.Bind(wx.EVT_BUTTON, self.OnSelect)

        newButton.Bind(wx.EVT_BUTTON, self.OnNew)

    def get_img_at_ind(self, ind):
        pth = os.path.join(img_folder, self.file_list[ind])
        return getImageToShow(pth, size=100, border=5)

    def updateImg(self) -> None:
        ind = self.shownImgInd
        img_to_show = self.get_img_at_ind(ind)
        self.img.SetBitmap(img_to_show)

    def OnNext(self, _) -> None:
        print("Next Image")
        self.shownImgInd += 1
        if self.shownImgInd == self.n_files - 1:
            self.next_button.Disable()
        if self.shownImgInd == 1:
            self.prev_button.Enable()
        self.updateImg()
        print("next img")

    def OnPrev(self, _) -> None:
        self.shownImgInd -= 1
        if self.shownImgInd == 0:
            self.prev_button.Disable()
        if self.shownImgInd == self.n_files - 2:
            self.next_button.Enable()
        self.updateImg()
        print("Prev img")

    def OnSelect(self, _):
        self.chosenImgInd = self.shownImgInd
        self.Close()

    def OnClose(self, _):
        print("Closed Change Date Dialog")
        self.Close()

    def OnNew(self, _):
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
    name = (
        "IMG_"
        + pad_int_str(wx_dt.GetYear(), 4)
        + pad_int_str(wx_dt.GetMonth() + 1)
        + pad_int_str(wx_dt.GetDay())
    )
    name = (
        f"{name}_"
        + pad_int_str(wx_dt.GetHour())
        + pad_int_str(wx_dt.GetMinute())
        + pad_int_str(wx_dt.GetSecond())
    )
    return name


def extract_date_from_image_name(img_file: str) -> Optional[wx.DateTime]:
    """Extracts the date information from the image name.

    Tries to extract the date and optionally the time.
    If extracted date is not valid or there is no date
    contained in the name, returns None.
    """
    p, filename = os.path.split(img_file)
    # Extract all numbers from string
    nums = re.findall(r"\d+", filename)
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
    month = rem // 100
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

    if not check_date_time(year, month, day, hour, mins, sec):
        print("Invalid date extracted!")
        return None

    # Check if date is valid
    wx_dt = wx.DateTime(day, month - 1, year, hour, mins, sec)
    return wx_dt if wx_dt.IsValid() else None


def get_time_from_file(img_file: str) -> wx.DateTime:
    """Tries to extract the date from a filename.

    If there is none, returns the modified time
    of the file as wx.DateTime.
    """
    name_date = extract_date_from_image_name(img_file)
    if name_date is None:
        name_date = get_file_modified_wx_dt(img_file)
    return name_date


def find_all_imgs_with_same_date(imgs_folder: str, img_name: str) -> List[str]:
    """Finds all files starting with string "img_name"
    in folder "img_folder".
    """
    res = []
    for f in os.listdir(imgs_folder):
        if f.startswith(img_name):
            res.append(f)
    return res


def find_new_name(
    img_name: str, same_date_file_list: List[str], ext: str, max_n_imgs: int = 10000
) -> str:
    """Chooses a new filename that is not in the list and
    contains the img_name in the beginning by appending an
    int to the filename separated by an underscore.
    """
    for k in range(max_n_imgs):
        new_name = img_name + "_" + str(k) + ext
        try:
            same_date_file_list.index(new_name)
        except ValueError:
            return img_name + "_" + str(k)

    # If there are already more than `max_n_imgs` images, gives up.
    raise ValueError("ERROR: Way too many fucking images.")


def copy_img_file_to_imgs(lf: str, img_date=None, photo_diag_fun: Callable = None):
    """Copy an image to the Img folder.

    If there exists one with
    the same date and time, a dialog pops up
    to let the user select if he wants to add
    text to an existing image or save the image
    If he doesn't decide, returns None
    """
    # Get date of image and find all images with same date
    imgDate = get_time_from_file(lf) if img_date is None else img_date
    imgName = get_img_name_from_time(imgDate)
    sameDateFileList = find_all_imgs_with_same_date(img_folder, imgName)
    print(sameDateFileList)

    # Get image type
    _, file_extension = os.path.splitext(lf)

    # Check if file with same datetime already exists
    if len(sameDateFileList) > 0:
        # Let the user look at the images and decide if he wants
        # to add the text to an already existing one instead of
        # adding the image in preview to the images.
        phDiag = PhotoWithSameDateExistsDialog(sameDateFileList)
        if photo_diag_fun is not None:
            wx.CallAfter(photo_diag_fun, phDiag)
        phDiag.ShowModal()
        phDiag.Destroy()
        ind = phDiag.chosenImgInd
        if ind is None:
            # No decision, abort
            return None
        if ind == -1:
            # Add image in preview
            imgName = find_new_name(imgName, sameDateFileList, file_extension)
        else:
            # Add text to existing image
            imgName = sameDateFileList[ind]
            return os.path.join(img_folder, imgName)

    # Add file extension and copy image to project
    imgName = imgName + file_extension
    copied_file_name = os.path.join(img_folder, imgName)
    copy2(lf, copied_file_name)
    return copied_file_name


def create_dir(dir_name: str) -> None:
    """Creates the given directory recursively.
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

    def OnDropFiles(self, x, y, filenames) -> bool:
        """Handle the dropped files.

        Checks if the extension is supported and stores
        the file path.
        """

        if len(filenames) > 1:
            print("Can only process one file at a time.")
        curr_file = filenames[0]
        _, ext = os.path.splitext(curr_file)
        ext = ext[1:].lower()
        if ext not in ["jpg", "jpeg", "png", "bmp"]:
            print(f"ERROR: Unsupported fucking file type: {ext}")
            return False

        # Get date and set image
        self.origImgDate = get_time_from_file(curr_file)
        self.frame.set_img_with_date(curr_file, self.origImgDate)
        self.loadedFile = curr_file

        return True


def format_date_time(date_time: wx.DateTime) -> str:
    """Format the given datetime in a string.
    """
    dt: wx.DateTime = date_time
    d, mon, y = dt.GetDay(), dt.GetMonth() + 1, dt.GetYear()
    h, m = pad_int_str(dt.GetHour()), pad_int_str(dt.GetMinute())
    s = pad_int_str(dt.GetSecond())

    str_out = f"{wx.DateTime.GetWeekDayName(dt.GetWeekDay())}, "
    str_out += f"{d}.{mon}.{y}, Time: {h}:{m}:{s}"
    return str_out


def getImageToShow(filename, size=180, border=5):
    """

    Assuming quadratic size.

    Args:
        filename:
        size:
        border:

    Returns:

    """
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


class ShowCapture(wx.Panel):
    """Panel that shows the content recorded by the webcam."""

    def __init__(self, parent, capture, fps: int = 25):

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
        self.timer.Start(1000.0 / fps)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)

    def getCurrFrame(self):
        ret, frame = self.capture.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, _):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(cv2.resize(frame, self.win_size), cv2.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(frame)
            self.Refresh()


class AcceptPhoto(TwoButtonDialogBase):
    """Dialog lets you look at the taken picture and
    decide if you want to take a new one or keep it
    """

    taken_img = None
    orig_img = None

    def __init__(self, parent=None, img=None, title="Accept photo?"):
        super().__init__(parent, title=title)

        if img is not None:
            self.set_img(img)
        self.SetSize((400, 400))
        self.SetTitle(title)
        self.accepted = False

    def InitUI(self):
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        height, width, c = self.taken_img.shape
        self.orig_img = self.taken_img
        height, width = (300, int(height / width * 300))
        new_size = height, width
        self.taken_img = cv2.resize(self.taken_img, new_size)
        bmp = wx.Bitmap.FromBuffer(height, width, self.taken_img.tobytes())
        bmp = wx.StaticBitmap(self, -1, bmp, size=new_size)
        self.v_box.Add(bmp, proportion=0, flag=wx.ALL, border=5)

        self.setup(pnl, "Accept", "Throw")

    def set_img(self, img):
        self.taken_img = img
        self.InitUI()

    def OnTakePic(self, e):
        print("Accepting img")
        self.accepted = True
        self.Close()

    # def Cleanup(self, destroy: bool = False):
    #     self.Destroy()

    def OnClose(self, e):
        print("Cancelled Accept Dialog")
        self.Close()


class SelfieDialog(TwoButtonDialogBase):
    """Dialog that lets you take a picture with the webcam.
    """

    taken_img = None
    dt_taken = None

    _vid_capture = None
    _img_cap = None

    accept_diag: AcceptPhoto

    def __init__(self, parent=None, title="Let me take a fucking selfie."):
        super().__init__(parent, title=title)

        self.InitUI()
        self.SetSize((400, 400))
        self.SetTitle(title)

        self.accept_diag = AcceptPhoto(None, img=None)

    def InitUI(self):
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self._vid_capture = cv2.VideoCapture(0)
        self._img_cap = ShowCapture(self, self._vid_capture)
        self.v_box.Add(self._img_cap, proportion=0, flag=wx.ALL, border=5)
        self._img_cap.Show()

        self.setup(pnl, "Shoot", "Cancel")
        # self.Bind(wx.EVT_CLOSE, self.release_cap)

    def OnTakePic(self, e, fun: Callable = None):
        """Takes a picture with the webcam.

        Captures the current frame and
        shows the Dialog that lets the user accept the photo or decide
        to take another one.
        """
        # accept_diag = AcceptPhoto(None, img=self._img_cap.getCurrFrame())
        self.accept_diag.set_img(self._img_cap.getCurrFrame())
        if fun is not None:
            wx.CallAfter(fun)
        self.accept_diag.ShowModal()
        if self.accept_diag.accepted:
            self.taken_img = self.accept_diag.orig_img
            self.release_cap()

    def release_cap(self, _=None):
        print("Releasing capture")
        self._vid_capture.release()
        cv2.destroyAllWindows()
        self.accept_diag.Destroy()
        self.Close()

    def Destroy(self):
        self._vid_capture.release()
        cv2.destroyAllWindows()
        self.accept_diag.Destroy()
        super().Destroy()

    def OnClose(self, e):
        print("Cancelled Selfie Dialog")
        self.release_cap()
