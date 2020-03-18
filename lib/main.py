"""The main frame.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
import shutil
from typing import Callable

import cv2
import wx

import lib
from lib import util
from lib.XML_write import save_entry, find_closest_entry
from lib.util import (
    FileDrop,
    icon_path,
    ChangeDateDialog,
    get_info_from_file,
    update_folder,
    scale_bitmap,
    format_date_time,
    getImageToShow,
    SelfieDialog,
    get_img_name_from_time,
    temp_folder,
    create_dir,
    create_xml_and_img_folder,
    write_folder_to_file,
    rep_newlines_with_space,
    copy_img_file_to_imgs,
    CustomMessageDialog,
)

ID_MENU_PHOTO = wx.Window.NewControlId()
ID_MENU_CHANGE_DATE = wx.Window.NewControlId()
ID_MENU_SELFIE = wx.Window.NewControlId()
ID_MENU_CHOOSE_DIR = wx.Window.NewControlId()
ID_MENU_IMPORT = wx.Window.NewControlId()
ID_CLICK_BUTTON = wx.Window.NewControlId()
ID_CLICK_OK_BUTTON = wx.Window.NewControlId()

LR_EXPAND = wx.LEFT | wx.RIGHT | wx.EXPAND


class StoryTimeApp(wx.Frame):
    """The Story Time App.

    This is the main frame, it contains all the functionality
    and opens other frames / dialogs when certain buttons
    are pushed.
    """

    count: int

    # GUI elements
    toolbar = None
    photoTool = None

    main_panel: wx.Panel
    fileDrop: FileDrop

    # Text
    input_text_field: wx.TextCtrl
    dateLabel: wx.StaticText
    cwd: wx.StaticText
    fix_text_box: wx.StaticText

    # Images
    img: wx.StaticBitmap
    image_drop_space: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    # Boxes
    v_box: wx.BoxSizer
    h_box_1: wx.BoxSizer
    h_box_cwd: wx.BoxSizer
    h_box_4: wx.BoxSizer

    def __init__(self, *args, **kwargs):
        super(StoryTimeApp, self).__init__(*args, **kwargs)
        self.defaultImg = os.path.join(icon_path, "default_img_txt.png")
        self.cdDialog = ChangeDateDialog(None, title="Change Date of entry")
        icon = wx.Icon()
        icon.CopyFromBitmap(
            wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY)
        )
        self.SetIcon(icon)
        files_path = get_info_from_file()
        update_folder(files_path)
        print("img_folder", util.img_folder)
        print("util.img_folder", util.img_folder)
        self.InitUI()
        self.SetSize((700, 700))
        self.SetTitle("Story Time")
        self.Center()

        self.imgLoaded = False

    def setup_toolbar(self) -> None:
        """Sets the toolbar up."""
        iconSize = (50, 50)

        self.toolbar = self.CreateToolBar()
        self.toolbar.SetToolBitmapSize(iconSize)

        tool_list = [
            ("save_icon.png", wx.ID_SAVE, "Save", "Save entry.", self.OnSave),
            (
                "photo_icon.png",
                ID_MENU_PHOTO,
                "Photo",
                "Change to photo mode.",
                self.OnPhoto,
                True,
            ),
            (
                "calendar_icon.png",
                ID_MENU_CHANGE_DATE,
                "Change",
                "Choose another date and time.",
                self.OnChangeDate,
            ),
            (
                "folder_icon.png",
                ID_MENU_CHOOSE_DIR,
                "Dir",
                "Change directory.",
                self.OnChangeDir,
            ),
            (
                "webcam_icon.png",
                ID_MENU_SELFIE,
                "Selfie",
                "Take a picture with your webcam.",
                self.OnSelfie,
            ),
        ]
        for ct, t in enumerate(tool_list):
            icon_name, tool_id, name, help_txt, met, *rest = t
            b_map = wx.Bitmap(os.path.join(icon_path, icon_name))
            icon = scale_bitmap(b_map, *iconSize)
            if rest is not None and rest:
                tool = self.toolbar.AddCheckTool(
                    tool_id, name, icon, shortHelp=help_txt
                )
            else:
                tool = self.toolbar.AddTool(tool_id, name, icon, shortHelp=help_txt)

            self.Bind(wx.EVT_TOOL, met, tool)
            tool_list[ct] = tool

        self.photoTool = tool_list[1]

        self.toolbar.AddSeparator()
        self.toolbar.Realize()

    def setup_one_line_static(self, lab: str, font):
        """Adds a static textbox spanning one line."""
        h_box_1 = wx.BoxSizer(wx.HORIZONTAL)
        stat_text = wx.StaticText(self.main_panel, label=lab)
        stat_text.SetFont(font)
        h_box_1.Add(stat_text, flag=wx.RIGHT, border=8)
        tc = wx.StaticText(self.main_panel)
        h_box_1.Add(tc, proportion=1)
        self.v_box.Add(h_box_1, flag=LR_EXPAND | wx.TOP, border=10)
        self.v_box.Add((-1, 10))
        return h_box_1, stat_text

    def InitUI(self) -> None:

        self.count = 5

        self.setup_toolbar()

        self.main_panel = wx.Panel(self)

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Date of entry
        lab = "Date: " + format_date_time(self.cdDialog.dt)
        self.h_box_1, self.dateLabel = self.setup_one_line_static(lab, font)

        # Working directory text
        self.h_box_cwd, self.cwd = self.setup_one_line_static(lib.util.data_path, font)

        # Text
        h_box_2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(self.main_panel, label="Input text below")
        st2.SetFont(font)
        h_box_2.Add(st2)
        self.v_box.Add(h_box_2, flag=wx.LEFT | wx.TOP, border=10)

        self.v_box.Add((-1, 10))

        # Text input field
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)
        self.input_text_field = wx.TextCtrl(self.main_panel, style=wx.TE_MULTILINE)
        h_box_3.Add(self.input_text_field, proportion=1, flag=wx.EXPAND)
        self.v_box.Add(h_box_3, proportion=1, flag=LR_EXPAND, border=10)

        self.v_box.Add((-1, 25))

        # Drop Target
        self.h_box_4 = wx.BoxSizer(wx.HORIZONTAL)
        self.bmp_shown = getImageToShow(self.defaultImg)
        self.img = wx.StaticBitmap(self.main_panel, -1, self.bmp_shown)
        self.image_drop_space = self.img
        self.image_drop_space.Hide()
        self.fileDrop = FileDrop(self.image_drop_space, self)
        self.image_drop_space.SetDropTarget(self.fileDrop)
        self.h_box_4.Add(self.image_drop_space, proportion=0, flag=wx.ALL, border=5)

        # Bottom right text field
        text_shown = "Default text."
        self.fix_text_box = wx.StaticText(
            self.main_panel, label=text_shown, style=wx.TE_MULTILINE, size=(-1, 190)
        )
        EXP_ALL = wx.EXPAND | wx.ALL
        self.h_box_4.Add(self.fix_text_box, proportion=1, flag=EXP_ALL, border=5)
        self.v_box.Add(self.h_box_4, proportion=1, flag=EXP_ALL, border=5)

        self.v_box.Add((-1, 25))

        # Buttons
        h_box_5 = wx.BoxSizer(wx.HORIZONTAL)
        btn1 = wx.Button(
            self.main_panel, ID_CLICK_OK_BUTTON, label="Save", size=(70, 30)
        )
        self.Bind(wx.EVT_BUTTON, self.OnOKButtonClick, id=ID_CLICK_OK_BUTTON)
        h_box_5.Add(btn1)
        btn2 = wx.Button(self.main_panel, ID_CLICK_BUTTON, label="Close", size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnCloseButtonClick, id=ID_CLICK_BUTTON)
        h_box_5.Add(btn2, flag=wx.LEFT | wx.BOTTOM, border=5)
        self.v_box.Add(h_box_5, flag=wx.ALIGN_RIGHT | wx.RIGHT, border=10)

        self.main_panel.SetSizer(self.v_box)

        self.update_preview_text()

        self.Bind(wx.EVT_CLOSE, self.Cleanup)

    def set_img(self, name: str) -> None:
        """Sets an image in the preview panel in photo mode.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.img.SetBitmap(self.bmp_shown)

    def set_img_with_date(self, curr_file: str, img_date: wx.DateTime) -> None:
        """Sets an image and updates the time.
        """
        self.update_date(img_date)
        self.imgLoaded = True
        self.set_img(curr_file)

    def OnSave(self, e) -> None:
        """Same as if the save button was clicked.
        """
        self.OnOKButtonClick(e)

    def OnSelfie(self, e, _diag_fun: Callable = None, _photo_fun: Callable = None) -> None:
        """Opens dialog that shows the webcam and lets you take a picture
        with it which is added to the preview window then.
        """
        # Go to photo mode if not there yet
        if not self.photoTool.IsToggled():
            # Abort if canceled
            if self.OnPhoto(e, _photo_fun) == -1:
                self.toolbar.ToggleTool(ID_MENU_PHOTO, False)
                return
            self.toolbar.ToggleTool(ID_MENU_PHOTO, True)

        # Show the dialog
        sDiag = SelfieDialog()
        if _diag_fun is not None:
            wx.CallAfter(_diag_fun, sDiag)
        sDiag.ShowModal()
        sDiag.Destroy()
        img = sDiag.taken_img

        # Save the image and show it in the preview
        if img is not None:
            curr_dt = wx.DateTime.Now()
            f_name = get_img_name_from_time(curr_dt) + "_Self.png"
            f_path = os.path.join(temp_folder, f_name)
            create_dir(temp_folder)
            cv2.imwrite(f_path, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.set_img_with_date(f_path, curr_dt)
            self.fileDrop.loadedFile = f_path

    def OnPhoto(self, _, _deb_fun: Callable = None) -> int:
        """Change to photo mode or back.

        If there is text in the textfield or an image loaded warn
        the user that it will be lost if he continues.
        """
        print("photoTool clicked")
        textStr = self.input_text_field.GetValue()
        if textStr != "" or self.imgLoaded:
            add_string = ", the loaded image" if self.imgLoaded else ""
            tog = self.photoTool.IsToggled()
            msg = f"If you change mode, the text{add_string} and the chosen time will be lost. Do you want to proceed?"

            md = CustomMessageDialog(
                msg,
                "Warning",
                self,
                ok_label="Fuck yeah!",
                cancel_label="No fucking way!",
            )
            if _deb_fun is not None:
                wx.CallAfter(_deb_fun, md)
            md.ShowModal()
            if not md.okay:
                self.toolbar.ToggleTool(ID_MENU_PHOTO, not tog)
                return -1
            else:
                self.remove_written_text()

        # Toggle the showing of the Image (drop space)
        if self.image_drop_space.IsShown():
            self.removeImg()
            self.imgLoaded = False
            self.image_drop_space.Hide()
        else:
            self.image_drop_space.Show()

        # Update date and time and the layout
        self.set_date_to_now()
        self.main_panel.Layout()
        return 0

    def OnCloseButtonClick(self, e):
        """Same as clicking X. Closes the application.
        """
        print("Close Button clicked")
        self.OnQuit(e)

    def removeImg(self):
        """Set the image in the image drop space to the default.
        """
        self.fileDrop.loadedFile = None
        self.set_img(self.defaultImg)
        self.imgLoaded = False

    def OnOKButtonClick(self, _):
        """Saves the text (and the photo in photo mode) in an XML entry.

        Does nothing if text (or image in photo mode) is missing.
        """

        # Check if there is any text at all
        textStr = self.input_text_field.GetValue()
        if textStr == "":
            wx.MessageBox("No fucking text!!", "Info", wx.OK | wx.ICON_EXCLAMATION)
            return

        # Check which mode is on
        tog = self.photoTool.IsToggled()
        if tog:
            # Check if there is an image
            lf = self.fileDrop.loadedFile
            if lf is None:
                wx.MessageBox("No fucking image!!", "Info", wx.OK | wx.ICON_EXCLAMATION)
                return

            # Save image entry
            curr_dat = self.cdDialog.dt
            copied_file_name = copy_img_file_to_imgs(lf, curr_dat)
            save_entry(textStr, curr_dat, "photo", copied_file_name)
        else:
            save_entry(textStr, self.cdDialog.dt)

        # Clear the contents
        self.removeImg()
        self.remove_written_text()

    def remove_written_text(self):
        """Clear text field and update date and time to now.
        """
        self.input_text_field.Clear()
        self.set_date_to_now()

    def OnChangeDate(self, _, _fun: Callable = None):
        """
        Shows dialog that lets the user change the current date.
        """
        if _fun is not None:
            wx.CallAfter(_fun, self.cdDialog)
        self.cdDialog.ShowModal()
        self.update_date()

    def OnChangeDir(self, _):
        """Shows dialog that lets the user change the current directory.
        """
        # Show dialog and get folder
        cdDiag = wx.DirDialog(None)
        cdDiag.ShowModal()
        files_path = cdDiag.GetPath()
        cdDiag.Destroy()

        # If none selected return
        if files_path == "" or files_path is None:
            print("No new folder selected.")
            return

        # Update and create data directories if not existing
        update_folder(files_path)
        self.cwd.SetLabelText(lib.util.data_path)
        create_xml_and_img_folder(files_path)
        self.set_date_to_now()

    def OnQuit(self, _):
        """Closing the app, writes the working directory to file for next use,
        empties temp folder and closes the app.

        Should always be executed before closing the app.
        """
        self.cdDialog.Destroy()
        write_folder_to_file()
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
        self.Close()

    def Cleanup(self, _):
        # Is this even used???
        print("Cleanup")
        self.cdDialog.Destroy()
        write_folder_to_file()
        self.Destroy()

    def set_date_to_now(self):
        """Updates the date and time to now.
        """
        self.update_date(wx.DateTime.Now())

    def update_date(self, new_date=None):
        """Updates the date to specified datetime.

        Updates the static datetime text and looks
        for the most recent XML text entries for text preview.
        """
        if new_date is not None:
            self.cdDialog.dt = new_date
        self.dateLabel.SetLabel("Date: " + format_date_time(self.cdDialog.dt))
        self.fix_text_box.SetLabel("This is a bug!")  # Probably unnecessary.
        self.update_preview_text()

    def _get_text_to_put(self, last: bool = True) -> str:
        ret_val = find_closest_entry(self.cdDialog.dt, not last)
        if ret_val is None:
            return ""
        date, child = ret_val
        child_text = (
            child.text
            if child.get("type") == "text"
            else "Photo: " + child.find("text").text
        )
        ret_str = "Last" if last else "Next"
        ret_str += " entry: " + format_date_time(date) + "\n\n"
        ret_str += rep_newlines_with_space(child_text) + "\n\n"
        return ret_str

    def update_preview_text(self):
        """Fills the static datetime text with the most recent entries
        for preview.
        """

        # Construct the text to put into the preview panel.
        text_to_put = ""
        text_to_put += self._get_text_to_put(True)
        text_to_put += self._get_text_to_put(False)
        if text_to_put == "":
            text_to_put = "No older entry present."

        # Set text and update layout
        self.fix_text_box.SetLabel(text_to_put)
        self.v_box.Layout()
