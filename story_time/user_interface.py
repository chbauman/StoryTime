"""The main frame.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
import shutil
from typing import Callable, List, Union, Optional, Tuple, Any

import cv2
import wx
from pkg_resources import resource_filename

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
    header_col,
    but_bg_col,
    text_bg_col,
    header_f_info,
    button_f_info,
    PhotoShow,
)


LR_EXPAND = wx.LEFT | wx.RIGHT | wx.EXPAND
EXPAND_ALL = wx.ALL | wx.EXPAND


class TextLinePanel(wx.Panel):
    stat_text: wx.StaticText

    def __init__(
        self,
        parent: wx.Frame,
        text: str = "Test Text",
        center_text: bool = False,
        bg_col: wx.Colour = "Red",
    ):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        s = wx.ALIGN_CENTRE_HORIZONTAL if center_text else wx.ALIGN_LEFT
        self.stat_text = wx.StaticText(self, label=text, style=s)
        self.stat_text.SetFont(wx.Font(header_f_info))
        box.Add(self.stat_text, 1, EXPAND_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour(bg_col)


class TwoButtonPanel(wx.Panel):
    def __init__(
        self,
        parent: wx.Frame,
        labels: List[str],
        center: bool = True,
        bg_col: wx.Colour = "Green",
    ):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        # Next and previous entry buttons
        self.but_1 = wx.Button(self, wx.ID_ANY, label=labels[0], size=(100, 35))
        self.but_2 = wx.Button(self, wx.ID_ANY, label=labels[1], size=(100, 35))
        self.but_1.SetFont(wx.Font(button_f_info))
        self.but_2.SetFont(wx.Font(button_f_info))

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
        self.SetBackgroundColour(bg_col)

    def set_but_methods(self, met_1: Callable, met_2: Callable) -> None:
        self.Bind(wx.EVT_BUTTON, met_1, id=self.but_1.Id)
        self.Bind(wx.EVT_BUTTON, met_2, id=self.but_2.Id)


class TextAndImgPanel(wx.Panel):
    text_box: Union[wx.TextCtrl, wx.StaticText]

    def __init__(
        self,
        parent: wx.Frame,
        editable: bool = False,
        drop_tgt: bool = False,
        bg_col: wx.Colour = wx.Colour(200, 255, 200),
    ):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)

        # The image
        img_name = f"default_img{'_txt' if drop_tgt else ''}.png"
        # self.default_img = os.path.join(icon_path, img_name)
        self.default_img = resource_filename(__name__, f"Icons/{img_name}")

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
        self.text_box.SetBackgroundColour(bg_col)

        EXP_ALL = wx.EXPAND | wx.ALL
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)

        h_box_3.Add(self.img, proportion=1, flag=EXP_ALL, border=5)
        h_box_3.Add(self.text_box, proportion=3, flag=EXP_ALL, border=5)

        box.Add(h_box_3, 1, EXP_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour(bg_col)


class ToolbarPanel(wx.Panel):
    tool_list = [
        (
            "save_icon.png",
            "Save",
            "Save entry.",
        ),
        (
            "photo_icon.png",
            "Photo",
            "Change to photo mode.",
            True,
        ),
        (
            "calendar_icon.png",
            "Change",
            "Choose another date and time.",
        ),
        (
            "folder_icon.png",
            "Dir",
            "Change directory.",
        ),
        (
            "webcam_icon.png",
            "Selfie",
            "Take a picture with your webcam.",
        ),
    ]
    tools: List[wx.ToolBarToolBase]
    photoTool: Union[Any, wx.ToolBarToolBase]

    def __init__(self, parent: wx.Frame, bg_col: wx.Colour = wx.Colour(140, 140, 255)):
        wx.Panel.__init__(self, parent)
        self.tools = []
        self.toolbar = wx.ToolBar(self, -1)
        self.setup_toolbar()
        self.SetBackgroundColour("Yellow")

        box = wx.BoxSizer(wx.VERTICAL)
        tb = self.toolbar
        box.Add(tb, 1, EXPAND_ALL, 0)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.toolbar.SetBackgroundColour(bg_col)

    def setup_toolbar(self) -> None:
        """Sets the toolbar up."""
        iconSize = (50, 50)

        self.toolbar.SetToolBitmapSize(iconSize)

        for ct, t in enumerate(self.tool_list):
            icon_name, name, help_txt, *rest = t
            tool_id = wx.Window.NewControlId()
            img_path = resource_filename(__name__, f"Icons/{icon_name}")
            icon = scale_bitmap(wx.Bitmap(img_path), *iconSize)
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

    def bind_tools(self, met_list: List[Callable]) -> None:
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
    photoTool: wx.ToolBarToolBase
    toolbar: wx.ToolBar
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

    prev_img_name = None

    curr_next_prev = None
    curr_prev_prev = None

    # Boxes
    v_box: wx.BoxSizer
    h_box_1: wx.BoxSizer
    h_box_cwd: wx.BoxSizer
    h_box_4: wx.BoxSizer

    next_prev_buttons: TwoButtonPanel

    # Data to keep track of the entry in the preview. `prev_dt` contains the
    # wx.DateTime of the previewed entry. If it reaches the end, it is either
    # `max_dt` or `min_dt`.
    prev_dt: wx.DateTime
    newest_reached: Optional[bool] = None
    max_dt: wx.DateTime = wx.DateTime(1, 1, 10000)
    min_dt: wx.DateTime = wx.DateTime(1, 1, 1)

    cdDialog: ChangeDateDialog
    default_img_drop: str
    default_img: str
    imgLoaded: bool

    @staticmethod
    def date_txt(dt: wx.DateTime) -> str:
        return f"Date: {format_date_time(dt)}"

    def set_date_txt(self, dt: wx.DateTime = None) -> None:
        """Sets the text in the date textbox."""
        if dt is None:
            dt = self.cdDialog.dt
        self.dateLabel.SetLabelText(self.date_txt(dt))

    def set_folder_txt(self) -> None:
        """Sets the text in the directory textbox."""
        self.cwd.SetLabelText("Working directory: " + story_time.util.data_path)

    def set_img(self, name: str) -> None:
        """Sets an image in the preview panel in photo mode.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.image_drop_space.SetBitmap(self.bmp_shown)

    def set_prev_img(self, name: str) -> None:
        """Sets an image in the entry preview panel.

        Given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.prev_img_space.SetBitmap(self.bmp_shown)
        self.prev_img_space.Show()

    def rem_prev_img(self) -> bool:
        """Removes the image by hiding it.

        Returns True if the image was removed and False if it
        way not necessary.
        """
        if self.prev_img_space.IsShown():
            self.prev_img_name = None
            self.prev_img_space.Hide()
            return True
        return False

    def set_img_with_date(self, curr_file: str, img_date: wx.DateTime) -> None:
        """Sets an image and updates the time."""
        self.update_date(img_date)
        self.imgLoaded = True
        self.set_img(curr_file)

        self.resized_layout()

    def OnSave(self, *args: Any, **kwargs: Any) -> None:
        """Same as if the save button was clicked."""
        self.OnOKButtonClick(*args, **kwargs)

    def on_taken_image_clicked(self, _: Any, _diag_fun: Callable = None) -> None:
        """Enlarges the shown image."""
        lf = self.fileDrop.loadedFile
        if lf is not None:
            ps = PhotoShow(self, lf)
            if _diag_fun is not None:
                wx.CallAfter(_diag_fun, ps)
            ps.ShowModal()

    def on_prev_image_clicked(self, _: Any, _diag_fun: Callable = None) -> None:
        """Enlarges the preview image."""
        prev_i = self.prev_img_name
        if prev_i is not None:
            ps = PhotoShow(self, prev_i)
            if _diag_fun is not None:
                wx.CallAfter(_diag_fun, ps)
            ps.ShowModal()

    def OnSelfie(
        self, e: Any, _diag_fun: Callable = None, _photo_fun: Callable = None
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
            self.fileDrop.loadedFile = f_path
            self.set_img_with_date(f_path, curr_dt)

    @staticmethod
    def toggle_prev_img(_: Any) -> None:
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
            md.SetSize((400, 300))
            if _deb_fun is not None:
                wx.CallAfter(_deb_fun, md)
            md.ShowModal()
            if not md.okay:
                return -1
            else:
                return 1
        return 0

    def OnPhoto(self, _: Any, _deb_fun: Callable = None) -> int:
        """Change to photo mode or back.

        If there is text in the textfield or an image loaded warn
        the user that it will be lost if he continues.
        """
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
        # self.set_date_to_now()
        self.resized_layout()
        return 0

    def removeImg(self) -> None:
        """Set the image in the image drop space to the default."""
        self.fileDrop.loadedFile = None
        self.set_img(self.default_img_drop)
        self.imgLoaded = False

    def OnOKButtonClick(self, _: Any, _no_text_fun: Callable = None) -> None:
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
        """Clear text field and update date and time to now."""
        self.input_text_field.Clear()
        self.set_date_to_now()

    def OnChangeDate(self, _: Any, _fun: Callable = None) -> None:
        """Shows dialog that lets the user change the current date."""
        if _fun is not None:
            wx.CallAfter(_fun, self.cdDialog)

        now = wx.DateTime.Now()
        self.cdDialog.dt = now
        cal_time = self.cdDialog.get_time()
        self.cdDialog.ShowModal()
        if self.cdDialog.dt != now and self.cdDialog.dt != cal_time:
            self.update_date()

    def OnChangeDir(self, _: Any) -> None:
        """Shows dialog that lets the user change the current directory."""
        # Show dialog and get folder
        files_path = util.ask_for_dir()

        # If none selected return
        if files_path == "" or files_path is None:
            return

        # Update and create data directories if not existing
        update_folder(files_path)
        self.cwd.SetLabelText(story_time.util.data_path)
        create_xml_and_img_folder(files_path)
        self.set_date_to_now()

    def OnX(self, _: Any, _deb_fun: Callable = None) -> None:
        """Called when the X is clicked to close.

        Also if self.Close() is called."""
        if self.check_if_discard_changes(_deb_fun) != -1:
            self.Cleanup(None)

    def Cleanup(self, _: Any) -> None:
        """Cleanup, should always be called when app is closed."""
        self.cdDialog.Destroy()
        write_folder_to_file()
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
        self.Destroy()

    def set_date_to_now(self) -> None:
        """Updates the date and time to now."""
        self.update_date(wx.DateTime.Now())

    def update_date(self, new_date: wx.DateTime = None) -> None:
        """Updates the date to specified datetime.

        Updates the static datetime text and looks
        for the most recent XML text entries for text preview.
        """
        if new_date is not None:
            self.cdDialog.dt = new_date
        new_lab = self.date_txt(self.cdDialog.dt)
        curr_lt = self.dateLabel.LabelText
        if curr_lt != new_lab:
            self.set_date_txt()
            self.prev_dt = self.cdDialog.dt
            self.update_preview_text(set_next=False)
            self.Layout()

    def _get_text_to_put(
        self, last: bool = True, set_img: bool = False, use_prev_dt: bool = False
    ) -> Tuple[str, bool]:
        search_dt = self.cdDialog.dt if not use_prev_dt else self.prev_dt
        ret_val = find_closest_entry(search_dt, not last)
        if ret_val is None:
            if use_prev_dt:
                self.newest_reached = not last
                self.prev_dt = self.min_dt if last else self.max_dt
                self.rem_prev_img()
            return "", True
        self.newest_reached = None
        child: Any
        date, child = ret_val
        is_text = child.get("type") == "text"
        child_text = child.text if is_text else "Photo: " + child.find("text").text
        changed_img = False
        if set_img:
            if not is_text:
                prev_img_name = child.find("photo").text
                new_p_img_name = os.path.join(
                    story_time.util.data_path, "Img", prev_img_name
                )
                if self.prev_img_name != new_p_img_name:
                    self.prev_img_name = new_p_img_name
                    changed_img = True
                    self.set_prev_img(self.prev_img_name)
            else:
                if self.prev_img_name is not None:
                    r = self.rem_prev_img()
                    changed_img = not r

        self.prev_dt = date
        ret_str = "Last" if last else "Next"
        ret_str += " entry: " + format_date_time(date) + "\n\n"
        ret_str += rep_newlines_with_space(child_text) + "\n\n"
        return ret_str, changed_img

    def update_preview_text(self, set_next: bool = None) -> None:
        """Fills the static datetime text with the most recent entries
        for preview.
        """

        # Construct the text to put into the preview panel.
        text_to_put = ""
        ch_img = True
        if set_next is not None:
            nxt, ch_img = self._get_text_to_put(not set_next, True, True)
            text_to_put += nxt
        else:
            prv, ch_img_prv = self._get_text_to_put(True, True)
            text_to_put += prv
            ch_img = ch_img or ch_img_prv
        if text_to_put == "":
            text_to_put = (
                f"No {'newer' if self.newest_reached else 'older'} entry present."
            )
            if self.newest_reached:
                self.next_prev_buttons.but_2.Disable()
                if not self.next_prev_buttons.but_1.IsEnabled():
                    self.next_prev_buttons.but_1.Enable()
            else:
                self.next_prev_buttons.but_1.Disable()
                if not self.next_prev_buttons.but_2.IsEnabled():
                    self.next_prev_buttons.but_2.Enable()
            if set_next is None:
                self.prev_dt = self.min_dt
        else:
            if not self.next_prev_buttons.but_2.IsEnabled():
                self.next_prev_buttons.but_2.Enable()
            if not self.next_prev_buttons.but_1.IsEnabled():
                self.next_prev_buttons.but_1.Enable()

        if self.fix_text_box.LabelText != text_to_put or ch_img:
            # Set text and update layout
            self.fix_text_box.SetLabel(text_to_put)
            self.v_box.Layout()

    def resized_layout(self) -> None:
        self.Layout()


class StoryTimeAppUI(StoryTimeApp):
    photoTool: wx.ToolBarToolBase
    toolbar: wx.ToolBar
    resized = True

    text_prev_sizer: wx.Sizer
    input_text_sizer: wx.Sizer

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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

    def next_entry(self, _: Any) -> None:
        self.update_preview_text(True)

    def prev_entry(self, _: Any) -> None:
        self.update_preview_text(False)

    def InitUI(self) -> None:

        # Setup toolbar
        met_list: List = [
            self.OnSave,
            self.OnPhoto,
            self.OnChangeDate,
            self.OnChangeDir,
            self.OnSelfie,
        ]
        tool_panel = ToolbarPanel(self, bg_col=header_col)
        tool_panel.bind_tools(met_list)
        self.photoTool = tool_panel.photoTool
        self.toolbar = tool_panel.toolbar

        path_text = TextLinePanel(
            self,
            text="Working directory: Path/to/the/working/directory",
            bg_col=header_col,
        )
        self.cwd = path_text.stat_text
        time_text = TextLinePanel(
            self,
            text="Current date and time: 12.12.1212, 23:12:55",
            center_text=True,
            bg_col=but_bg_col,
        )
        self.dateLabel = time_text.stat_text

        # Buttons
        self.next_prev_buttons = TwoButtonPanel(
            self, labels=["Previous", "Next"], bg_col=but_bg_col
        )

        self.next_prev_buttons.set_but_methods(self.prev_entry, self.next_entry)
        save_close_buttons = TwoButtonPanel(
            self, labels=["Save", "Close"], center=True, bg_col=but_bg_col
        )
        save_close_buttons.set_but_methods(self.OnOKButtonClick, self.OnX)

        # Text and images
        text_edit = TextAndImgPanel(
            self, editable=True, drop_tgt=True, bg_col=text_bg_col
        )
        text_edit.SetMinSize((200, 200))
        self.fileDrop = text_edit.fileDrop
        self.image_drop_space = text_edit.img
        self.image_drop_space.Bind(wx.EVT_LEFT_DOWN, self.on_taken_image_clicked)
        self.input_text_sizer = text_edit.GetSizer()
        self.input_text_field = text_edit.text_box

        text_preview = TextAndImgPanel(self, editable=False, bg_col=text_bg_col)
        text_preview.SetMinSize((200, 200))
        self.text_prev_sizer = text_preview.GetSizer()
        self.fix_text_box = text_preview.text_box
        self.prev_img_space = text_preview.img
        self.prev_img_space.Bind(wx.EVT_LEFT_DOWN, self.on_prev_image_clicked)

        # Put it all together
        box = wx.BoxSizer(wx.VERTICAL)
        # box.Add(tool_panel, 0, wx.ALIGN_CENTER_HORIZONTAL)
        box.Add(tool_panel, 0, LR_EXPAND)
        box.Add(time_text, 0, LR_EXPAND)
        box.Add(text_edit, 1, LR_EXPAND)
        box.Add(save_close_buttons, 0, LR_EXPAND)
        box.Add(text_preview, 1, LR_EXPAND)
        box.Add(self.next_prev_buttons, 0, LR_EXPAND)
        box.Add(path_text, 0, LR_EXPAND)
        box.Fit(self)
        self.v_box = box
        self.main_panel = box
        self.SetSizer(box)

        # Prepare UI
        self.update_preview_text()
        self.set_date_txt()
        self.set_folder_txt()
        self.Bind(wx.EVT_CLOSE, self.OnX)

        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        self.SetMinSize((400, 600))

    def on_resize(self, _: Any) -> None:
        self.resized = True  # set dirty
        self.Layout()

    def OnIdle(self, _: Any) -> None:
        if self.resized:
            lf = self.fileDrop.loadedFile
            s_min = min(self.input_text_sizer.Size)
            if s_min > 30:
                set_img = self.default_img_drop if lf is None else lf
                self.image_drop_space.SetBitmap(getImageToShow(set_img, s_min - 30))

            if self.prev_img_name is not None:
                s_min = min(self.text_prev_sizer.Size)
                if s_min > 30:
                    self.prev_img_space.SetBitmap(
                        getImageToShow(self.prev_img_name, s_min - 30)
                    )

            self.Layout()
            self.resized = False  # reset the flag

    def resized_layout(self) -> None:
        self.on_resize(None)
        self.OnIdle(None)

    def set_prev_img(self, name: str) -> None:
        """Sets an image in the entry preview panel.

        Given the path of the image.
        """
        super().set_prev_img(name)

        self.resized_layout()

    pass
