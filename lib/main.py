"""The main frame.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
import shutil
from typing import Sequence

import cv2
import wx

from lib import util
from lib.XML_write import saveEntryInXml, addImgs, convertFromTxt, getLastXMLEntry
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
    copy_img_file_to_imgs)

ID_MENU_PHOTO = wx.NewId()
ID_MENU_CHANGE_DATE = wx.NewId()
ID_MENU_SELFIE = wx.NewId()
ID_MENU_CHOOSE_DIR = wx.NewId()
ID_MENU_IMPORT = wx.NewId()
ID_CLICK_BUTTON = wx.NewId()
ID_CLICK_OK_BUTTON = wx.NewId()

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
    fix_text_box: wx.StaticText

    # Images
    img: wx.StaticBitmap
    image_drop_space: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    # Boxes
    v_box: wx.BoxSizer
    h_box_1: wx.BoxSizer
    h_box_4: wx.BoxSizer

    def __init__(self, *args, **kwargs):
        super(StoryTimeApp, self).__init__(*args, **kwargs)
        self.defaultImg = os.path.join(icon_path, "default_img.png")
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
        self.SetSize((700, 600))
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
                "import_icon.png",
                ID_MENU_IMPORT,
                "Import",
                "Import text or images from old version.",
                self.OnImport,
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
                tool = self.toolbar.AddCheckTool(tool_id, name, icon, shortHelp=help_txt)
            else:
                tool = self.toolbar.AddTool(tool_id, name, icon, shortHelp=help_txt)

            self.Bind(wx.EVT_TOOL, met, tool)
            tool_list[ct] = tool

        self.photoTool = tool_list[1]

        self.toolbar.AddSeparator()
        self.toolbar.Realize()

    def InitUI(self):

        self.count = 5

        self.setup_toolbar()

        self.main_panel = wx.Panel(self)

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Datum
        self.h_box_1 = wx.BoxSizer(wx.HORIZONTAL)
        lab = "Date: " + format_date_time(self.cdDialog.dt)
        self.dateLabel = wx.StaticText(self.main_panel, label=lab)
        self.dateLabel.SetFont(font)
        self.h_box_1.Add(self.dateLabel, flag=wx.RIGHT, border=8)
        tc = wx.StaticText(self.main_panel)
        self.h_box_1.Add(tc, proportion=1)
        self.v_box.Add(self.h_box_1, flag=LR_EXPAND | wx.TOP, border=10)

        self.v_box.Add((-1, 10))

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

    def set_img(self, name):
        """Sets an image in the preview panel in photo mode.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.img.SetBitmap(self.bmp_shown)

    def set_img_with_date(self, curr_file, img_date):
        """Sets an image and updates the time.
        """
        self.update_date(img_date)
        self.imgLoaded = True
        self.set_img(curr_file)

    def OnSave(self, e):
        """Same as if the save button was clicked.
        """
        self.OnOKButtonClick(e)

    def OnSelfie(self, e):
        """Opens dialog that shows the webcam and lets you take a picture
        with it which is added to the preview window then.
        """
        # Go to photo mode if not there yet
        if not self.photoTool.IsToggled():
            # Abort if canceled
            if self.OnPhoto(e) == -1:
                self.toolbar.ToggleTool(ID_MENU_PHOTO, False)
                return
            self.toolbar.ToggleTool(ID_MENU_PHOTO, True)

        # Show the dialog
        sDiag = SelfieDialog()
        sDiag.ShowModal()
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

        # Cleanup
        sDiag.Destroy()

    def OnPhoto(self, _):
        """Change to photo mode or back.

        If there is text in the textfield or an image loaded warn
        the user that it will be lost if he continues.
        """
        textStr = self.input_text_field.GetValue()
        if textStr != "" or self.imgLoaded:
            add_string = ", the loaded image" if self.imgLoaded else ""
            tog = self.photoTool.IsToggled()
            msg = f"If you change mode, the text{add_string} and the chosen time will be lost. Do you want to proceed?"
            dial = wx.MessageDialog(
                None, msg, "Warning", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
            )
            dial.SetYesNoLabels("Fuck yeah!", "No fucking way!")
            ans = dial.ShowModal()
            if ans == wx.ID_NO:
                # Toggle back
                self.toolbar.ToggleTool(ID_MENU_PHOTO, not tog)
                return -1
            elif ans == wx.ID_YES:
                self.remove_written_text()
            else:
                print("WTF")

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
        print("photoTool clicked")

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
            saveEntryInXml(textStr, curr_dat, "photo", copied_file_name)
        else:
            saveEntryInXml(textStr, self.cdDialog.dt)

        # Clear the contents
        self.removeImg()
        self.remove_written_text()

    def remove_written_text(self):
        """Clear text field and update date and time to now.
        """
        self.input_text_field.Clear()
        self.set_date_to_now()

    def OnChangeDate(self, _):
        """
        Shows dialog that lets the user change the current date.
        """
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
        create_xml_and_img_folder(files_path)
        self.set_date_to_now()

    def OnImport(self, _):
        msg = "Do you want to add images in a folder or text entries from a .txt file?"
        flags = wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.CANCEL_DEFAULT
        dial = wx.MessageDialog(None, msg, "Question", flags)
        dial.SetYesNoLabels("Text of course!", "Fucking images!")
        imp_imgs = None
        ans = dial.ShowModal()
        if ans == wx.ID_NO:
            imp_imgs = True
        elif ans == wx.ID_YES:
            imp_imgs = False

        print("Fuck, ", imp_imgs)
        if imp_imgs is None:
            return

        if imp_imgs:
            cdDiag = wx.DirDialog(None, message="Hoi", name="Choose Location")
            cdDiag.ShowModal()
            files_path = cdDiag.GetPath()
            if files_path == "" or files_path is None:
                print("Null String")
                return
            addImgs(files_path)
        else:
            wc, style = "Text files (*.txt)|*.txt", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            with wx.FileDialog(
                self, "Open Text file", wildcard=wc, style=style
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind

                pathname = fileDialog.GetPath()
                try:
                    convertFromTxt(pathname)
                except IOError:
                    wx.LogError("Cannot open file '%s'." % pathname)
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

    @staticmethod
    def _get_text_to_put(date_and_text: Sequence = None, last: bool = True) -> str:
        if date_and_text is None:
            return ""
        ret_str = "Last" if last else "Next"
        ret_str += format_date_time(date_and_text[0]) + "\n\n"
        ret_str += rep_newlines_with_space(date_and_text[1]) + "\n\n"
        return ret_str

    def update_preview_text(self):
        """Fills the static datetime text with the most recent entries
        for preview.
        """
        # Get most recent last and next XML text entries (if existing).
        date_and_text = getLastXMLEntry(self.cdDialog.dt)
        next_date_and_text = getLastXMLEntry(self.cdDialog.dt, True)

        # Construct the text to put into the preview panel.
        text_to_put = ""
        text_to_put += self._get_text_to_put(date_and_text, True)
        text_to_put += self._get_text_to_put(next_date_and_text, False)
        if text_to_put == "":
            text_to_put = "No older entry present."

        # Set text and update layout
        self.fix_text_box.SetLabel(text_to_put)
        self.v_box.Layout()
