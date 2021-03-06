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
from typing import List, Callable, Sequence, Optional, Any

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
info_file = resource_filename(__name__, "Info.txt")

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
header_f_info = wx.FontInfo(12).Family(wx.FONTFAMILY_SWISS).Bold()
button_f_info = wx.FontInfo(12).Family(wx.FONTFAMILY_SWISS).Bold()
dialog_f_info = wx.FontInfo(17).Family(wx.FONTFAMILY_SWISS).Bold()


def update_folder(new_data_path: str) -> None:
    """Update global path variables if data folder is changed."""
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
    """Create a folder for the XML and the image files in `base_folder`."""
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


def ask_for_dir(_fun: Callable = None, show: bool = True) -> str:
    """Ask the user to select a directory."""
    dial_text = "Choose directory to store Imgs and Text data."
    flags = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
    cdDiag = wx.DirDialog(None, dial_text, "", flags)
    if _fun is not None:
        _fun(cdDiag)
    cdDiag.ShowModal() if show else None
    return cdDiag.GetPath()


def get_info_from_file(ask: bool = True, _fun: Callable = None) -> str:
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
        else:
            assert ask
            files_path = story_time.util.ask_for_dir(_fun)
            create_xml_and_img_folder(files_path)
            return files_path


def write_folder_to_file() -> None:
    """Write the current working directory to file `info_file`."""
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


class PhotoShow(wx.Dialog):
    okay: bool = False
    resized = False

    f_name: str

    def __init__(self, parent: wx.Frame, f_name: str) -> None:
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
        self.SetTitle("Large photo view")
        wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        self.f_name = f_name
        b = getImageToShow(f_name)
        self.imageCtrl = wx.StaticBitmap(self, wx.ID_ANY, b)
        self.v_box.Add(self.imageCtrl, 0, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(self.v_box)

        self.SetBackgroundColour(text_bg_col)
        self.Size = wx.Size(500, 500)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnSize(self, _: Any) -> None:
        self.resized = True  # set dirty

    def OnIdle(self, _: Any) -> None:
        if self.resized:
            # take action if the dirty flag is set
            self.Layout()
            s = self.v_box.Size
            self.imageCtrl.SetBitmap(getImageToShow(self.f_name, s[1], width=s[0]))
            self.resized = False  # reset the flag


class ButtonDialogBase(wx.Dialog):
    """Base class for a dialog with a button."""

    v_box: wx.BoxSizer

    def setup_v_box(
        self, h_box: wx.BoxSizer, h_button: wx.Button, pnl: wx.Panel
    ) -> None:
        h_box.Add(h_button, flag=wx.LEFT, border=5)
        self.v_box.Add(pnl, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)
        self.v_box.Add(
            h_box, proportion=1, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10
        )
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
    ) -> None:
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

    def OnTakePic(self, e: Any) -> None:
        pass

    def OnClose(self, e: Any) -> None:
        pass


class CustomMessageDialog(TwoButtonDialogBase):
    okay: bool = False

    def __init__(
        self,
        message: str = None,
        title: str = "Message",
        *args: Any,
        cancel_only: bool = False,
        ok_label: str = "Ok",
        cancel_label: str = "Cancel",
        **kw: Any,
    ) -> None:
        super().__init__(*args, **kw)
        self.SetTitle(title)
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        if message is not None:
            stMsg = wx.StaticText(self, -1, message)
            stMsg.SetFont(wx.Font(dialog_f_info))
            # stMsg.SetBackgroundColour(green)
            self.v_box.Add(stMsg, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(self.v_box)

        if cancel_only:
            h_box = wx.BoxSizer(wx.HORIZONTAL)
            cancel_butt = wx.Button(self, label=cancel_label)
            cancel_butt.Bind(wx.EVT_BUTTON, self.OnOK)
            cancel_butt.SetFont(wx.Font(button_f_info))
            self.setup_v_box(h_box, cancel_butt, pnl)
        else:
            self.setup(pnl, ok_label, cancel_label, self.OnOK, self.OnClose)

    def OnOK(self, _: Any) -> None:
        self.okay = True
        self.Close()

    def OnClose(self, _: Any) -> None:
        self.Close()


class ChangeDateDialog(TwoButtonDialogBase):
    """Date and Time picker dialog"""

    start_dt: wx.DateTime
    dt: wx.DateTime
    cal: wx.adv.CalendarCtrl
    timePicker: wx.adv.TimePickerCtrl

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(ChangeDateDialog, self).__init__(*args, **kw)

        self.set_time_now()
        self.InitUI()

        self.SetSize((400, 400))
        self.SetTitle("Change Date of entry")

    def InitUI(self) -> None:
        pnl = wx.Panel(self)

        # Define UI elements
        top_text = wx.StaticText(self, label="Select Date and Time")
        top_text.SetFont(wx.Font(dialog_f_info))
        self.cal = wx.adv.CalendarCtrl(self)
        time_txt = wx.StaticText(self, label="Time: ")
        self.timePicker = wx.adv.TimePickerCtrl(self, dt=self.dt)

        # Define extra button
        now_button = wx.Button(self, label="Choose now")
        now_button.Bind(wx.EVT_BUTTON, self.set_now_and_close)
        now_button.SetFont(wx.Font(button_f_info))

        # Define sizer for time
        sbs = wx.BoxSizer(wx.HORIZONTAL)
        sbs.Add(time_txt, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        sbs.Add(self.timePicker, flag=wx.ALL, border=5)

        # Define top-level sizer
        self.v_box = wx.BoxSizer(wx.VERTICAL)
        self.v_box.Add(top_text, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(sbs, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(self.cal, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(now_button, flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        self.setup(pnl, "Ok", "Cancel", self.OnOK, self.OnClose)

    def set_time_now(self) -> None:
        """Sets the time to now."""
        self.dt = wx.DateTime.Now()

    def set_now_and_close(self, _: Any) -> None:
        self.set_time_now()
        self.OnClose(None)

    def get_time(self) -> wx.DateTime:
        timeTuple = self.timePicker.GetTime()
        dt = self.cal.GetDate()
        dt.SetHour(timeTuple[0])
        dt.SetMinute(timeTuple[1])
        dt.SetSecond(timeTuple[2])
        return dt

    def OnClose(self, e: Any) -> None:
        self.Close()

    def OnOK(self, _: Any) -> None:
        """Sets `self.dt` to the current time."""
        self.dt = self.get_time()
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
        parent: wx.Frame = None,
        title: str = "Image with same date already exists",
    ) -> None:
        super(PhotoWithSameDateExistsDialog, self).__init__(parent, title=title)

        self.file_list = file_list
        self.chosenImgInd: Optional[int] = None
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

    def get_img_at_ind(self, ind: int) -> wx.Bitmap:
        pth = os.path.join(img_folder, self.file_list[ind])
        return getImageToShow(pth, 100, border=5)

    def updateImg(self) -> None:
        ind = self.shownImgInd
        img_to_show = self.get_img_at_ind(ind)
        self.img.SetBitmap(img_to_show)

    def OnNext(self, _: Any) -> None:
        self.shownImgInd += 1
        if self.shownImgInd == self.n_files - 1:
            self.next_button.Disable()
        if self.shownImgInd == 1:
            self.prev_button.Enable()
        self.updateImg()

    def OnPrev(self, _: Any) -> None:
        self.shownImgInd -= 1
        if self.shownImgInd == 0:
            self.prev_button.Disable()
        if self.shownImgInd == self.n_files - 2:
            self.next_button.Enable()
        self.updateImg()

    def OnSelect(self, _: Any) -> None:
        self.chosenImgInd = self.shownImgInd
        self.Close()

    def OnClose(self, _: Any) -> None:
        self.Close()

    def OnNew(self, _: Any) -> None:
        self.chosenImgInd = -1  # This means new
        self.Close()


def datetime_to_wx_datetime(date: datetime) -> wx.DateTime:
    """Converts a python datetime to a wx.DateTime."""
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
    """Gives the image basename from the wx.DateTime."""
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
        return None
    date = int(nums[0])
    # Year must be greater than 1
    if date < 10000:
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


def copy_img_file_to_imgs(
    lf: str, img_date: wx.DateTime = None, photo_diag_fun: Callable = None
) -> Optional[str]:
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
    """Creates the given directory recursively."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return


class FileDrop(wx.FileDropTarget):
    """Drop Target to drop images to be added."""

    origImgDate = None

    def __init__(self, window: Any, frame: Any) -> None:

        wx.FileDropTarget.__init__(self)
        self.window = window
        self.frame = frame
        self.loadedFile = None
        self.newFileName = None

    def OnDropFiles(self, x: Any, y: Any, filenames: List) -> bool:
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
    """Format the given datetime in a string."""
    dt: wx.DateTime = date_time
    d, mon, y = dt.GetDay(), dt.GetMonth() + 1, dt.GetYear()
    h, m = pad_int_str(dt.GetHour()), pad_int_str(dt.GetMinute())
    s = pad_int_str(dt.GetSecond())

    str_out = f"{wx.DateTime.GetWeekDayName(dt.GetWeekDay())}, "
    str_out += f"{d}.{mon}.{y}, Time: {h}:{m}:{s}"
    return str_out


def getImageToShow(
    filename: str, height: int = 180, border: int = 5, width: int = None
) -> wx.Bitmap:
    """Converts the specified image to a bitmap of according size.

    Preserves the aspect ratio by padding with a color.

    Args:
        filename: The path to the file.
        height: The size of the returned image.
        border: Border width.
        width: The width of the returned image, same as height if not specified.

    Returns:
        The bitmap with the specified size
    """
    bor_2 = 2 * border
    border_col = green

    # Load from file and convert to image
    wxBmp = wx.Bitmap(filename)
    image = wxBmp.ConvertToImage()

    # Handle sizes
    if width is None:
        width = height

    # Reserve space for border
    height -= bor_2
    width -= bor_2

    imgSize = image.GetSize()
    img_w, img_h = imgSize
    too_high = img_h / img_w > height / width
    fac = height / img_h if too_high else width / img_w

    # Rescale image
    image.Rescale(
        int(round(fac * img_w)), int(round(fac * img_h)), wx.IMAGE_QUALITY_HIGH
    )
    new_img_w, new_img_h = image.GetSize()

    # Pad image
    border_w = border + (width - new_img_w) // 2
    border_h = border + (height - new_img_h) // 2
    img_sz = wx.Size(width + bor_2, height + bor_2)
    image.Resize(
        img_sz,
        wx.Point(border_w, border_h),
        border_col[0],
        border_col[1],
        border_col[2],
    )

    # Convert to bitmap and return
    result = wx.Bitmap(image)
    return result


class ShowCapture(wx.Panel):
    """Panel that shows the content recorded by the webcam."""

    def __init__(self, parent: Any, capture: Any, fps: int = 25) -> None:

        # Capture first frame to get size
        self.capture = capture
        ret, frame = self.capture.read()
        height, width = frame.shape[:2]
        self.h_by_w = height / width
        self.win_size = (300, int(round(self.h_by_w * 300)))

        wx.Panel.__init__(self, parent, wx.ID_ANY, (0, 0), self.win_size)
        parent.SetSize(self.win_size)

        self.h, self.w = self.win_size
        frame = cv2.cvtColor(cv2.resize(frame, self.win_size), cv2.COLOR_BGR2RGB)
        self.bmp = wx.Bitmap.FromBuffer(self.h, self.w, frame)

        self.timer = wx.Timer(self)
        self.timer.Start(int(round(1000.0 / fps)))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)

    def getCurrFrame(self) -> Any:
        ret, frame = self.capture.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def OnPaint(self, _: Any) -> None:
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, _: Any) -> None:
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

    def __init__(
        self, parent: wx.Frame = None, img: str = None, title: str = "Accept photo?"
    ) -> None:
        super().__init__(parent, title=title)

        if img is not None:
            self.set_img(img)
        self.SetSize((400, 350))
        self.SetTitle(title)
        self.accepted = False

    def InitUI(self) -> None:
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        assert self.taken_img is not None
        height, width, c = self.taken_img.shape
        self.orig_img = self.taken_img
        height, width = (300, int(height / width * 300))
        new_size = height, width
        self.taken_img = cv2.resize(self.taken_img, new_size)
        bmp = wx.Bitmap.FromBuffer(height, width, self.taken_img.tobytes())
        bmp = wx.StaticBitmap(self, -1, bmp, size=new_size)
        self.v_box.Add(
            bmp, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border=5
        )

        self.setup(pnl, "Accept", "Throw")

    def set_img(self, img: str) -> None:
        self.taken_img = img
        self.InitUI()

    def OnTakePic(self, e: Any) -> None:
        self.accepted = True
        self.Close()

    def OnClose(self, e: Any) -> None:
        self.Close()


class SelfieDialog(TwoButtonDialogBase):
    """Dialog that lets you take a picture with the webcam."""

    taken_img = None
    dt_taken = None

    _vid_capture: cv2.VideoCapture
    _img_cap: ShowCapture

    accept_diag: AcceptPhoto

    def __init__(self, parent: Any = None, title: str = "Take a selfie") -> None:
        super().__init__(parent, title=title)

        self.InitUI()
        self.SetSize((400, 350))
        self.SetTitle(title)

        self.accept_diag = AcceptPhoto(None, img=None)

    def InitUI(self) -> None:
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self._vid_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self._img_cap = ShowCapture(self, self._vid_capture)
        self.v_box.Add(
            self._img_cap,
            proportion=0,
            flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL,
            border=5,
        )
        self._img_cap.Show()
        self.setup(pnl, "Shoot", "Cancel")

    def OnTakePic(self, e: Any, fun: Callable = None) -> None:
        """Takes a picture with the webcam.

        Captures the current frame and
        shows the Dialog that lets the user accept the photo or decide
        to take another one.
        """
        curr_f: Any = self._img_cap.getCurrFrame()
        self.accept_diag.set_img(curr_f)
        if fun is not None:
            wx.CallAfter(fun)
        self.accept_diag.ShowModal()
        if self.accept_diag.accepted:
            self.taken_img = self.accept_diag.orig_img
            self.release_cap()

    def release_cap(self, _: Any = None) -> None:
        self._vid_capture.release()
        cv2.destroyAllWindows()
        self.accept_diag.Destroy()
        self.Close()

    def OnClose(self, e: Any) -> None:
        self.release_cap()
