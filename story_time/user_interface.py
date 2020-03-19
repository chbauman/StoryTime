"""The main frame.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
import shutil
from typing import Callable, List, Union, Optional

import cv2
import wx

import story_time
from story_time import util
from story_time.XML_write import save_entry, find_closest_entry
from story_time.util import (
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
ID_CLICK_NEXT_ENTRY = wx.Window.NewControlId()
ID_CLICK_PREVIOUS_ENTRY = wx.Window.NewControlId()

LR_EXPAND = wx.LEFT | wx.RIGHT | wx.EXPAND
EXPAND_ALL = wx.ALL | wx.EXPAND


class TextLinePanel(wx.Panel):
    stat_text: wx.StaticText

    def __init__(self, parent, text: str = "Test Text", center_text: bool = False):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        s = wx.ALIGN_CENTRE_HORIZONTAL if center_text else wx.ALIGN_LEFT
        self.stat_text = wx.StaticText(self, label=text, style=s)
        box.Add(self.stat_text, 1, wx.ALIGN_CENTER_HORIZONTAL | EXPAND_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour("Red")


class TwoButtonPanel(wx.Panel):
    def __init__(self, parent, labels: List[str], center: bool = True):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        # Next and previous entry buttons
        self.but_1 = wx.Button(self, wx.ID_ANY, label=labels[0], size=(70, 30))
        self.but_2 = wx.Button(self, wx.ID_ANY, label=labels[1], size=(70, 30))

        h_box_p_but = wx.BoxSizer(wx.HORIZONTAL)
        h_box_p_but.Add(self.but_1)
        h_box_p_but.Add(self.but_2, flag=wx.LEFT, border=5)

        flags = (
            wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM
            if center
            else wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM
        )
        box.Add(h_box_p_but, 1, flags, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour("Green")

    def set_but_methods(self, met_1, met_2):
        self.Bind(wx.EVT_BUTTON, met_1, id=self.but_1.Id)
        self.Bind(wx.EVT_BUTTON, met_2, id=self.but_2.Id)


class TextAndImgPanel(wx.Panel):
    text_box: Union[wx.TextCtrl, wx.StaticText]

    def __init__(self, parent, editable: bool = False, drop_tgt: bool = False):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)

        # The image
        img_name = f"default_img{'_txt' if drop_tgt else ''}.png"
        self.default_img = os.path.join(icon_path, img_name)
        self.bmp_shown = getImageToShow(self.default_img)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        if drop_tgt:
            self.img.Hide()
            self.fileDrop = FileDrop(self.img, parent)
            self.img.SetDropTarget(self.fileDrop)
        self.img.Hide()

        # Text field
        text_shown = "Default text."
        kws = {"style": wx.TE_MULTILINE, "size": (-1, 180)}
        if editable:
            self.text_box = wx.TextCtrl(self, **kws)
        else:
            self.text_box = wx.StaticText(self, label=text_shown, **kws)
        self.text_box.SetBackgroundColour(wx.Colour(200, 255, 200))

        EXP_ALL = wx.EXPAND | wx.ALL
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)
        h_box_3.Add(self.text_box, proportion=1, flag=EXP_ALL, border=5)
        h_box_3.Add(self.img, proportion=0, flag=wx.ALL, border=5)

        box.Add(h_box_3, 1, EXP_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour("Blue")


class ToolbarPanel(wx.Panel):
    tool_list = [
        ("save_icon.png", "Save", "Save entry.",),
        ("photo_icon.png", "Photo", "Change to photo mode.", True,),
        ("calendar_icon.png", "Change", "Choose another date and time.",),
        ("folder_icon.png", "Dir", "Change directory.",),
        ("webcam_icon.png", "Selfie", "Take a picture with your webcam.",),
    ]
    tools = None
    photoTool = None

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.tools = []
        self.toolbar = wx.ToolBar(self, -1)
        self.setup_toolbar()
        self.SetBackgroundColour("Yellow")

        box = wx.BoxSizer(wx.VERTICAL)
        tb = self.toolbar
        box.Add(tb, 1, wx.ALIGN_RIGHT | EXPAND_ALL, 0)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.toolbar.SetBackgroundColour(wx.Colour(140, 140, 255))

    def setup_toolbar(self) -> None:
        """Sets the toolbar up."""
        iconSize = (50, 50)

        self.toolbar.SetToolBitmapSize(iconSize)

        for ct, t in enumerate(self.tool_list):
            icon_name, name, help_txt, *rest = t
            tool_id = wx.Window.NewControlId()
            b_map = wx.Bitmap(os.path.join(icon_path, icon_name))
            icon = scale_bitmap(b_map, *iconSize)
            args = (tool_id, name, icon)
            fun = (
                self.toolbar.AddCheckTool
                if rest is not None and rest
                else self.toolbar.AddTool
            )
            tool = fun(*args, shortHelp=help_txt)
            self.tools.append(tool)

        self.photoTool = self.tools[1]

        self.toolbar.AddSeparator()
        self.toolbar.Realize()

    def bind_tools(self, met_list: List[Callable]):
        assert len(met_list) == 5 == len(self.tools), f"Tools: {self.tools}"
        for met, tool in zip(met_list, self.tools):
            self.Bind(wx.EVT_TOOL, met, tool)

    pass


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

    main_panel: Union[wx.BoxSizer, wx.Panel]
    fileDrop: FileDrop

    # Text
    input_text_field: wx.TextCtrl
    dateLabel: wx.StaticText
    cwd: wx.StaticText
    fix_text_box: wx.StaticText

    # Images
    img: wx.StaticBitmap
    image_drop_space: wx.StaticBitmap
    img_prev: wx.StaticBitmap
    prev_img_space: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    # Boxes
    v_box: wx.BoxSizer
    h_box_1: wx.BoxSizer
    h_box_cwd: wx.BoxSizer
    h_box_4: wx.BoxSizer

    # Data to keep track of the entry in the preview. `prev_dt` contains the
    # wx.DateTime of the previewed entry. If it reaches the end, it is either
    # `max_dt` or `min_dt`.
    prev_dt: wx.DateTime
    newest_reached: Optional[bool] = None
    max_dt: wx.DateTime = wx.DateTime(1, 1, 10000)
    min_dt: wx.DateTime = wx.DateTime(1, 1, 1)

    def __init__(self, *args, **kwargs):
        super(StoryTimeApp, self).__init__(*args, **kwargs)
        self.default_img_drop = os.path.join(icon_path, "default_img_txt.png")
        self.default_img = os.path.join(icon_path, "default_img.png")
        self.cdDialog = ChangeDateDialog(None, title="Change Date of entry")
        icon = wx.Icon()
        icon.CopyFromBitmap(
            wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY)
        )
        self.SetIcon(icon)
        files_path = get_info_from_file()
        update_folder(files_path)
        print("util.img_folder", util.img_folder)
        self.InitUI()
        self.SetSize((700, 800))
        self.SetTitle("Story Time")
        self.Center()

        self.imgLoaded = False

    def setup_toolbar(self, panel: wx.Panel = None) -> None:
        """Sets the toolbar up."""
        iconSize = (50, 50)

        self.toolbar = self.CreateToolBar() if panel is None else panel.CreateToolBar()
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

        self.main_panel = wx.Panel(self)

        self.setup_toolbar()
        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Date of entry
        self.h_box_1, self.dateLabel = self.setup_one_line_static("Date", font)

        # Working directory text
        self.h_box_cwd, self.cwd = self.setup_one_line_static("This/is/a/Bug", font)
        # self.cwd.SetBackgroundColour("Yellow")

        # Text
        self.setup_one_line_static("Input text below", font)

        # Text input field
        self.input_text_field = wx.TextCtrl(
            self.main_panel, style=wx.TE_MULTILINE, size=(-1, 180)
        )

        # Drop Target
        self.bmp_shown = getImageToShow(self.default_img_drop)
        self.image_drop_space = wx.StaticBitmap(self.main_panel, -1, self.bmp_shown)
        self.image_drop_space.Hide()
        self.fileDrop = FileDrop(self.image_drop_space, self)
        self.image_drop_space.SetDropTarget(self.fileDrop)

        # Preview text field
        text_shown = "Default text."
        self.fix_text_box = wx.StaticText(
            self.main_panel, label=text_shown, style=wx.TE_MULTILINE, size=(-1, 180)
        )

        # Preview image field
        self.bmp_shown = getImageToShow(self.default_img)
        self.img_prev = wx.StaticBitmap(self.main_panel, -1, self.bmp_shown)
        self.prev_img_space = self.img_prev
        self.prev_img_space.Hide()

        # Next and previous entry buttons
        next_but = wx.Button(
            self.main_panel, ID_CLICK_NEXT_ENTRY, label="Next", size=(70, 30)
        )
        self.Bind(wx.EVT_BUTTON, self.toggle_prev_img, id=ID_CLICK_NEXT_ENTRY)
        prev_but = wx.Button(
            self.main_panel, ID_CLICK_PREVIOUS_ENTRY, label="Previous", size=(70, 30)
        )
        self.Bind(wx.EVT_BUTTON, self.toggle_prev_img, id=ID_CLICK_PREVIOUS_ENTRY)

        h_box_p_but = wx.BoxSizer(wx.HORIZONTAL)
        h_box_p_but.Add(prev_but)
        h_box_p_but.Add(next_but, flag=wx.LEFT, border=5)

        # Add stuff to horizontal boxes
        EXP_ALL = wx.EXPAND | wx.ALL
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)
        h_box_3.Add(self.fix_text_box, proportion=1, flag=EXP_ALL, border=5)
        h_box_3.Add(self.prev_img_space, proportion=0, flag=wx.ALL, border=5)
        self.h_box_4 = wx.BoxSizer(wx.HORIZONTAL)
        self.h_box_4.Add(self.input_text_field, proportion=1, flag=EXP_ALL, border=5)
        self.h_box_4.Add(self.image_drop_space, proportion=0, flag=wx.ALL, border=5)

        # Add to vertical box
        self.v_box.Add(self.h_box_4, proportion=1, flag=EXP_ALL, border=5)
        # self.v_box.Add((-1, 25))

        self.v_box.Add(h_box_p_but, flag=LR_EXPAND | wx.TOP, border=5)
        # self.v_box.Add((-1, 25))

        self.v_box.Add(h_box_3, proportion=1, flag=LR_EXPAND, border=10)
        self.v_box.Add((-1, 25))

        # Save and close buttons
        btn1 = wx.Button(
            self.main_panel, ID_CLICK_OK_BUTTON, label="Save", size=(70, 30)
        )
        self.Bind(wx.EVT_BUTTON, self.OnOKButtonClick, id=ID_CLICK_OK_BUTTON)
        btn2 = wx.Button(self.main_panel, ID_CLICK_BUTTON, label="Close", size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnCloseButtonClick, id=ID_CLICK_BUTTON)

        h_box_5 = wx.BoxSizer(wx.HORIZONTAL)
        h_box_5.Add(btn1)
        h_box_5.Add(btn2, flag=wx.LEFT | wx.BOTTOM, border=5)
        self.v_box.Add(h_box_5, flag=wx.ALIGN_RIGHT | wx.RIGHT, border=10)

        self.main_panel.SetSizer(self.v_box)

        self.update_preview_text()
        self.set_date_txt()
        self.set_folder_txt()

        self.Bind(wx.EVT_CLOSE, self.OnQuit)

    def set_date_txt(self):
        """Sets the text in the date textbox."""
        self.dateLabel.SetLabelText("Date: " + format_date_time(self.cdDialog.dt))

    def set_folder_txt(self):
        """Sets the text in the directory textbox."""
        self.cwd.SetLabelText("Working directory: " + story_time.util.data_path)

    def set_img(self, name: str) -> None:
        """Sets an image in the preview panel in photo mode.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.image_drop_space.SetBitmap(self.bmp_shown)

    def set_prev_img(self, name: str):
        """Sets an image in the entry preview panel.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.prev_img_space.SetBitmap(self.bmp_shown)
        self.prev_img_space.Show()

    def rem_prev_img(self):
        """Removes the image by hiding it."""
        if self.prev_img_space.IsShown():
            self.prev_img_space.Hide()

    def set_img_with_date(self, curr_file: str, img_date: wx.DateTime) -> None:
        """Sets an image and updates the time.
        """
        self.update_date(img_date)
        self.imgLoaded = True
        self.set_img(curr_file)

    def OnSave(self, *args, **kwargs) -> None:
        """Same as if the save button was clicked.
        """
        self.OnOKButtonClick(*args, **kwargs)

    def OnSelfie(
        self, e, _diag_fun: Callable = None, _photo_fun: Callable = None
    ) -> None:
        """Opens dialog that shows the webcam and lets you take a picture
        with it which is added to the preview window then.
        """
        # Go to photo mode if not there yet
        if not self.photoTool.IsToggled():
            # Abort if canceled
            if self.OnPhoto(e, _photo_fun) == -1:
                self.toolbar.ToggleTool(self.photoTool.Id, False)
                return
            self.toolbar.ToggleTool(self.photoTool.Id, True)

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

    @staticmethod
    def toggle_prev_img(_):
        """Toggles the preview image."""
        print("Toggling")
        pass

    def check_if_discard_changes(self, _deb_fun: Callable = None) -> int:
        """Checks whether there is unsaved info.

        Returns 0 if there is None, 1 if it may be discarded
        and -1 if the user wants to keep it."""
        textStr = self.input_text_field.GetValue()
        if textStr != "" or self.imgLoaded:
            add_string = ", the loaded image" if self.imgLoaded else ""
            msg = (
                f"If you proceed, the text{add_string} and the chosen "
                f"time will be lost. Do you want to proceed?"
            )
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
                return -1
            else:
                return 1
        return 0

    def OnPhoto(self, _, _deb_fun: Callable = None) -> int:
        """Change to photo mode or back.

        If there is text in the textfield or an image loaded warn
        the user that it will be lost if he continues.
        """
        print("photoTool clicked")
        discard_int = self.check_if_discard_changes(_deb_fun)
        if discard_int == -1:
            tog = self.photoTool.IsToggled()
            self.toolbar.ToggleTool(self.photoTool.Id, not tog)
            return -1
        elif discard_int == 1:
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

    def OnCloseButtonClick(self, *args, **kwargs) -> None:
        """Same as clicking X. Closes the application.
        """
        print("Close Button clicked")
        self.OnQuit(*args, **kwargs)

    def removeImg(self) -> None:
        """Set the image in the image drop space to the default.
        """
        self.fileDrop.loadedFile = None
        self.set_img(self.default_img_drop)
        self.imgLoaded = False

    def OnOKButtonClick(self, _, _no_text_fun: Callable = None) -> None:
        """Saves the text (and the photo in photo mode) in an XML entry.

        Does nothing if text (or image in photo mode) is missing.
        """

        # Check if there is any text at all
        textStr = self.input_text_field.GetValue()
        if textStr == "":
            md = CustomMessageDialog(
                "No fucking text specified!!",
                "Info",
                self,
                cancel_only=True,
                cancel_label="Got it",
            )
            if _no_text_fun is not None:
                wx.CallAfter(_no_text_fun, md)
            md.ShowModal()
            return

        # Check which mode is on
        tog = self.photoTool.IsToggled()
        if tog:
            # Check if there is an image
            lf = self.fileDrop.loadedFile
            if lf is None:
                md = CustomMessageDialog(
                    "No fucking image specified!!",
                    "Info",
                    self,
                    cancel_only=True,
                    cancel_label="Got it",
                )
                if _no_text_fun is not None:
                    wx.CallAfter(_no_text_fun, md)
                md.ShowModal()
                # wx.MessageBox("No fucking image!!", "Info", wx.OK | wx.ICON_EXCLAMATION)
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

    def remove_written_text(self) -> None:
        """Clear text field and update date and time to now.
        """
        self.input_text_field.Clear()
        self.set_date_to_now()

    def OnChangeDate(self, _, _fun: Callable = None) -> None:
        """
        Shows dialog that lets the user change the current date.
        """
        if _fun is not None:
            wx.CallAfter(_fun, self.cdDialog)
        self.cdDialog.ShowModal()
        self.update_date()

    def OnChangeDir(self, _) -> None:
        """Shows dialog that lets the user change the current directory.
        """
        # Show dialog and get folder
        files_path = util.ask_for_dir()

        # If none selected return
        if files_path == "" or files_path is None:
            print("No new folder selected.")
            return

        # Update and create data directories if not existing
        update_folder(files_path)
        self.cwd.SetLabelText(story_time.util.data_path)
        create_xml_and_img_folder(files_path)
        self.set_date_to_now()

    def OnX(self, _, _deb_fun: Callable = None):
        """Called when the X is clicked to close.

        Also if self.Close() is called."""
        print("OnX")
        if self.check_if_discard_changes(_deb_fun) == -1:
            print("Not exiting because of unsaved data.")
            return
        self.Cleanup(None)

    def OnQuit(self, _, _deb_fun: Callable = None) -> None:
        """Closing the app, writes the working directory to file for next use,
        empties temp folder and closes the app.
        """
        print("Quit")
        if self.check_if_discard_changes(_deb_fun) != -1:
            self.Cleanup(None)

    def Cleanup(self, _) -> None:
        # Is this even used???
        print("Cleanup")
        self.cdDialog.Destroy()
        write_folder_to_file()
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
        self.Destroy()

    def set_date_to_now(self) -> None:
        """Updates the date and time to now.
        """
        self.update_date(wx.DateTime.Now())

    def update_date(self, new_date: wx.DateTime = None) -> None:
        """Updates the date to specified datetime.

        Updates the static datetime text and looks
        for the most recent XML text entries for text preview.
        """
        if new_date is not None:
            self.cdDialog.dt = new_date
        self.dateLabel.SetLabel("Date: " + format_date_time(self.cdDialog.dt))
        # The line below is probably unnecessary.
        # Actually has already been helpful in some cases!
        self.fix_text_box.SetLabel("This is a bug!")
        self.prev_dt = self.cdDialog.dt
        self.update_preview_text(set_next=False)

    def _get_text_to_put(
        self, last: bool = True, set_img: bool = False, use_prev_dt: bool = False
    ) -> str:
        search_dt = self.cdDialog.dt if not use_prev_dt else self.prev_dt
        ret_val = find_closest_entry(search_dt, not last)
        if ret_val is None:
            if use_prev_dt:
                self.newest_reached = not last
                self.prev_dt = self.min_dt if last else self.max_dt
                self.rem_prev_img()
            return ""
        self.newest_reached = None
        date, child = ret_val
        is_text = child.get("type") == "text"
        child_text = child.text if is_text else "Photo: " + child.find("text").text
        if set_img:
            if not is_text:
                img_name = child.find("photo").text
                img_path = os.path.join(story_time.util.data_path, "Img", img_name)
                self.set_prev_img(img_path)
            else:
                self.rem_prev_img()

        self.prev_dt = date
        ret_str = "Last" if last else "Next"
        ret_str += " entry: " + format_date_time(date) + "\n\n"
        ret_str += rep_newlines_with_space(child_text) + "\n\n"
        return ret_str

    def update_preview_text(self, set_next: bool = None) -> None:
        """Fills the static datetime text with the most recent entries
        for preview.
        """

        # Construct the text to put into the preview panel.
        text_to_put = ""
        if set_next is not None:
            text_to_put += self._get_text_to_put(not set_next, True, True)
        else:
            text_to_put += self._get_text_to_put(True, True)
        if text_to_put == "":
            text_to_put = (
                f"No {'newer' if self.newest_reached else 'older'} entry present."
            )
            if set_next is None:
                self.prev_dt = self.min_dt

        # Set text and update layout
        self.fix_text_box.SetLabel(text_to_put)
        self.v_box.Layout()


class StoryTimeAppUITest(StoryTimeApp):
    photoTool = None
    toolbar = None

    def __init__(self, *args, **kwargs):
        super(StoryTimeApp, self).__init__(*args, **kwargs)
        self.default_img_drop = os.path.join(icon_path, "default_img_txt.png")
        self.default_img = os.path.join(icon_path, "default_img.png")
        self.cdDialog = ChangeDateDialog(None, title="Change Date of entry")
        icon = wx.Icon()
        icon.CopyFromBitmap(
            wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY)
        )
        self.SetIcon(icon)
        files_path = get_info_from_file()
        update_folder(files_path)
        print("util.img_folder", util.img_folder)
        self.InitUI()
        self.SetSize((700, 800))
        self.SetTitle("Story Time")
        self.Center()

        self.imgLoaded = False

    def next_entry(self, _):
        self.update_preview_text(True)

    def prev_entry(self, _):
        self.update_preview_text(False)

    def InitUI(self) -> None:

        # Setup toolbar
        met_list = [
            self.OnSave,
            self.OnPhoto,
            self.OnChangeDate,
            self.OnChangeDir,
            self.OnSelfie,
        ]
        tool_panel = ToolbarPanel(self)
        tool_panel.bind_tools(met_list)
        self.photoTool = tool_panel.photoTool
        self.toolbar = tool_panel.toolbar

        path_text = TextLinePanel(
            self, text="Working directory: Path/to/the/working/directory"
        )
        self.cwd = path_text.stat_text
        time_text = TextLinePanel(
            self, text="Current date and time: 12.12.1212, 23:12:55", center_text=True
        )
        self.dateLabel = time_text.stat_text

        # Buttons
        next_prev_buttons = TwoButtonPanel(self, labels=["Previous", "Next"])

        next_prev_buttons.set_but_methods(self.prev_entry, self.next_entry)
        save_close_buttons = TwoButtonPanel(
            self, labels=["Save", "Close"], center=False
        )
        save_close_buttons.set_but_methods(
            self.OnOKButtonClick, self.OnCloseButtonClick
        )

        # Text and images
        text_edit = TextAndImgPanel(self, editable=True, drop_tgt=True)
        self.fileDrop = text_edit.fileDrop
        self.image_drop_space = text_edit.img
        self.input_text_field = text_edit.text_box
        text_preview = TextAndImgPanel(self, editable=False)
        self.fix_text_box = text_preview.text_box
        self.prev_img_space = text_preview.img

        # Put it all together
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(path_text, 0, LR_EXPAND)
        box.Add(tool_panel, 0, LR_EXPAND)
        box.Add(time_text, 0, LR_EXPAND)
        box.Add(text_edit, 1, LR_EXPAND)
        box.Add(save_close_buttons, 0, LR_EXPAND)
        box.Add(text_preview, 1, LR_EXPAND)
        box.Add(next_prev_buttons, 0, LR_EXPAND)
        box.Fit(self)
        self.v_box = box
        self.main_panel = box
        self.SetSizer(box)

        # Prepare UI
        self.update_preview_text()
        self.set_date_txt()
        self.set_folder_txt()
        self.Bind(wx.EVT_CLOSE, self.OnX)

    pass
