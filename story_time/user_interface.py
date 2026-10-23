"""The main frame.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
from typing import Any, Callable, Optional, Union

import cv2
import wx

import story_time
from story_time import util
from story_time.texts import tr
from story_time.util import (
    ChangeDateDialog,
    CustomMessageDialog,
    FileDrop,
    NoWebcamError,
    PhotoShow,
    SelfieDialog,
    bar_text_col,
    but_bg_col,
    copy_img_file_to_imgs,
    create_xml_and_img_folder,
    datetime_to_wx_datetime,
    format_date_time,
    get_data_folder,
    get_img_name_from_time,
    get_temp_folder,
    getImageToShow,
    header_col,
    header_f_info,
    header_text_col,
    icon_path,
    remove_temp_folder,
    resource_filename,
    save_data_folder,
    scale_bitmap,
    text_bg_col,
    update_folder,
)
from story_time.XML_write import (
    Entry,
    filter_entries,
    group_by_month,
    load_all_entries,
    save_entry,
)


def shortcut_for(
    key: int, ctrl: bool, alt: bool, shift: bool, in_text_input: bool
) -> Optional[str]:
    """Returns the name of the action of a keyboard shortcut, if there is one.

    The arrow keys are only used if the cursor is not in the text input or the
    list, as they are needed there to move around. With Alt they always work.

    Args:
        key: The key code.
        ctrl: Whether Ctrl (Cmd on macOS) is pressed.
        alt: Whether Alt is pressed.
        shift: Whether Shift is pressed.
        in_text_input: Whether the text input or the list has the keyboard focus.
    """
    if shift:
        return None
    if ctrl and not alt and 0 < key < 256:
        return CTRL_SHORTCUTS.get(chr(key).upper())
    if key in (wx.WXK_LEFT, wx.WXK_RIGHT) and not ctrl and (alt or not in_text_input):
        return "prev" if key == wx.WXK_LEFT else "next"
    return None


#: Actions of the shortcuts with Ctrl, by the letter of the key.
CTRL_SHORTCUTS = {
    "N": "new",
    "S": "save",
    "P": "photo",
    "D": "date",
    "O": "folder",
    "T": "selfie",
    "Q": "quit",
}

LR_EXPAND = wx.LEFT | wx.RIGHT | wx.EXPAND
SIDEBAR_WIDTH = 340  #: Initial width of the list of the entries.
MAX_IMAGE_SIZE = 400  #: Maximum edge length of the shown images in pixels.
MAX_LABEL_TEXT = 28  #: Maximum number of characters of an entry in the list.
EXPAND_ALL = wx.ALL | wx.EXPAND


class TextLinePanel(wx.Panel):
    stat_text: wx.StaticText

    def __init__(
        self,
        parent: wx.Frame,
        text: str = "Test Text",
        center_text: bool = False,
        bg_col: wx.Colour = header_col,
        text_col: wx.Colour = header_text_col,
    ):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        s = wx.ALIGN_CENTRE_HORIZONTAL if center_text else wx.ALIGN_LEFT
        self.stat_text = wx.StaticText(self, label=text, style=s)
        self.stat_text.SetFont(wx.Font(header_f_info))
        self.stat_text.SetForegroundColour(text_col)
        box.Add(self.stat_text, 1, EXPAND_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour(bg_col)


class TextAndImgPanel(wx.Panel):
    text_box: wx.TextCtrl

    def __init__(
        self,
        parent: wx.Frame,
        editable: bool = False,
        drop_tgt: bool = False,
        bg_col: wx.Colour = text_bg_col,
        frame: Optional[wx.Frame] = None,
    ):
        """
        Args:
            parent: The parent window.
            editable: Whether it is the text input (otherwise a read-only text).
            drop_tgt: Whether the image is a drop target for image files.
            bg_col: The background color.
            frame: The main frame that gets the dropped files, default `parent`.
        """
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)

        # The image
        img_name = f"default_img{'_txt' if drop_tgt else ''}.png"
        # self.default_img = os.path.join(icon_path, img_name)
        self.default_img = resource_filename(f"Icons/{img_name}")

        self.bmp_shown = getImageToShow(self.default_img)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        if drop_tgt:
            self.img.Hide()
            self.fileDrop = FileDrop(self.img, frame or parent)
            self.img.SetDropTarget(self.fileDrop)
        self.img.Hide()

        # Text field
        text_shown = "Default text."
        kws = {"style": wx.TE_MULTILINE, "size": (-1, 180)}
        if editable:
            self.text_box = wx.TextCtrl(self, **kws)
        else:
            # Read-only, but scrollable to be able to read long entries
            kws["style"] |= wx.TE_READONLY | wx.BORDER_NONE
            self.text_box = wx.TextCtrl(self, value=text_shown, **kws)
        self.text_box.SetBackgroundColour(bg_col)

        EXP_ALL = wx.EXPAND | wx.ALL
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)

        h_box_3.Add(self.img, proportion=1, flag=wx.ALL | wx.ALIGN_TOP, border=5)
        h_box_3.Add(self.text_box, proportion=3, flag=EXP_ALL, border=5)

        box.Add(h_box_3, 1, EXP_ALL, 5)
        box.Fit(self)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.SetBackgroundColour(bg_col)


def entry_label(entry: Entry) -> str:
    """The text of an entry in the list: day, time and the first line."""
    dt = entry.date_time
    weekday = wx.DateTime.GetWeekDayName(
        datetime_to_wx_datetime(dt).GetWeekDay(), wx.DateTime.Name_Abbr
    )
    text = entry.first_line
    if len(text) > MAX_LABEL_TEXT:
        text = text[: MAX_LABEL_TEXT - 1].rstrip() + "\u2026"
    if entry.type == "photo":
        text = f"{tr('main.list.photo')} {text}".strip()
    return f"{dt.day}. {weekday}  {dt:%H:%M}  {text}"


def month_label(year: int, month: int) -> str:
    """The text of a month in the list."""
    return f"{wx.DateTime.GetMonthName(month - 1, wx.DateTime.Name_Full)} {year}"


class EntryListPanel(wx.Panel):
    """Searchable list of the entries, newest first and grouped by month."""

    def __init__(
        self,
        parent: wx.Window,
        on_select: Callable[[Entry], None],
        bg_col: wx.Colour = text_bg_col,
    ):
        """
        Args:
            parent: The parent window.
            on_select: Called with the entry when the user selects one.
            bg_col: The background color.
        """
        wx.Panel.__init__(self, parent)
        self.on_select = on_select
        self.entries: list[Entry] = []
        #: The shown entries in the order of the list, with their tree items.
        self.shown: list[tuple[Entry, wx.TreeItemId]] = []
        self._notify = True

        self.search = wx.SearchCtrl(self)
        self.search.SetDescriptiveText(tr("main.list.search_hint"))
        self.search.ShowCancelButton(True)
        self.tree = wx.TreeCtrl(
            self,
            style=wx.TR_HIDE_ROOT
            | wx.TR_HAS_BUTTONS
            | wx.TR_LINES_AT_ROOT
            | wx.TR_NO_LINES
            | wx.TR_FULL_ROW_HIGHLIGHT
            | wx.TR_SINGLE,
        )
        self.info = wx.StaticText(self, label="")
        self.tree.SetBackgroundColour(bg_col)
        self.SetBackgroundColour(bg_col)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.search, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(self.tree, 1, wx.EXPAND)
        box.Add(self.info, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(box)

        self.search.Bind(wx.EVT_TEXT, lambda _: self.refresh())
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)

    def set_entries(self, entries: list[Entry]) -> None:
        """Sets all entries, newest first. Keeps the selection if possible."""
        self.entries = entries
        self.refresh()

    def refresh(self) -> None:
        """Rebuilds the tree, only with the entries matching the search."""
        query = self.search.GetValue()
        selected = self.selected_entry()
        shown = filter_entries(self.entries, query)

        self._notify = False
        try:
            self.tree.Freeze()
            self.tree.DeleteAllItems()
            root = self.tree.AddRoot("")
            self.shown = []
            for n, ((year, month), group) in enumerate(group_by_month(shown)):
                month_item = self.tree.AppendItem(root, month_label(year, month))
                for entry in group:
                    item = self.tree.AppendItem(month_item, entry_label(entry))
                    self.tree.SetItemData(item, entry)
                    self.shown.append((entry, item))
                # Show the newest month, or everything if searching
                if n == 0 or query.strip():
                    self.tree.Expand(month_item)
            for entry, item in self.shown:
                if entry == selected:
                    self.tree.SelectItem(item)
                    self.tree.EnsureVisible(item)
            self.tree.Thaw()
        finally:
            self._notify = True

        if not self.entries:
            self.info.SetLabel(tr("main.list.empty"))
        elif not shown:
            self.info.SetLabel(tr("main.list.no_match"))
        else:
            self.info.SetLabel("")
        self.Layout()

    def selected_entry(self) -> Optional[Entry]:
        """The selected entry, None if none or a month is selected."""
        item = self.tree.GetSelection()
        if not item.IsOk():
            return None
        data = self.tree.GetItemData(item)
        return data if isinstance(data, Entry) else None

    def clear_selection(self) -> None:
        """Deselects the entry without notifying."""
        self._notify = False
        try:
            self.tree.Unselect()  # `UnselectAll` does nothing for a single selection
        finally:
            self._notify = True

    def select_entry(self, entry: Entry, notify: bool = False) -> bool:
        """Selects the given entry, returns whether it is in the list."""
        for shown_entry, item in self.shown:
            if shown_entry == entry:
                self._notify = notify
                try:
                    self.tree.SelectItem(item)
                    self.tree.EnsureVisible(item)
                finally:
                    self._notify = True
                return True
        return False

    def select_adjacent(self, step: int) -> bool:
        """Selects the entry `step` positions further down in the list.

        Selects the first one if none is selected. Does not go past the ends.
        Returns whether the selection changed.
        """
        if not self.shown:
            return False
        selected = self.selected_entry()
        index = next((i for i, (e, _) in enumerate(self.shown) if e == selected), None)
        new_index = (
            0 if index is None else min(max(index + step, 0), len(self.shown) - 1)
        )
        if new_index == index:
            return False
        return self.select_entry(self.shown[new_index][0], notify=True)

    def _on_tree_selection(self, _: Any) -> None:
        entry = self.selected_entry()
        if self._notify and entry is not None:
            self.on_select(entry)


class ToolbarPanel(wx.Panel):
    #: Icon file, key of the texts, keyboard shortcut and whether it is a toggle tool.
    tool_list = [
        ("new_icon.png", "toolbar.new", "Ctrl+N", True),
        ("save_icon.png", "toolbar.save", "Ctrl+S"),
        ("photo_icon.png", "toolbar.photo", "Ctrl+P", True),
        ("calendar_icon.png", "toolbar.date", "Ctrl+D"),
        ("folder_icon.png", "toolbar.folder", "Ctrl+O"),
        ("webcam_icon.png", "toolbar.selfie", "Ctrl+T"),
    ]
    tools: list[wx.ToolBarToolBase]
    photoTool: Union[Any, wx.ToolBarToolBase]
    new_tool: wx.ToolBarToolBase
    folder_tool: wx.ToolBarToolBase
    #: The tools that are only needed to write an entry.
    edit_tools: list[wx.ToolBarToolBase]

    def __init__(self, parent: wx.Frame, bg_col: wx.Colour = header_col):
        wx.Panel.__init__(self, parent)
        self.tools = []
        self.toolbar = wx.ToolBar(self, -1)
        self.setup_toolbar()
        self.SetBackgroundColour(header_col)

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

        for t in self.tool_list:
            icon_name, text_key, shortcut, *rest = t
            name = tr(f"{text_key}.name")
            help_txt = self.tool_help(text_key, shortcut)
            tool_id = wx.Window.NewControlId()
            img_path = resource_filename(f"Icons/{icon_name}")
            icon = scale_bitmap(wx.Bitmap(img_path), *iconSize)
            args = (tool_id, name, icon)
            fun = (
                self.toolbar.AddCheckTool
                if rest is not None and rest
                else self.toolbar.AddTool
            )
            tool = fun(*args, shortHelp=help_txt)
            self.tools.append(tool)

        self.new_tool = self.tools[0]
        self.photoTool = self.tools[2]
        self.folder_tool = self.tools[4]
        self.edit_tools = [self.tools[i] for i in (1, 2, 3, 5)]

        self.toolbar.AddSeparator()
        self.toolbar.Realize()

    @staticmethod
    def tool_help(text_key: str, shortcut: str, extra: str = "") -> str:
        """The tooltip of a tool, with its shortcut and optionally more info."""
        return f"{tr(f'{text_key}.help')} ({shortcut})" + (
            f"\n{extra}" if extra else ""
        )

    def bind_tools(self, met_list: list[Callable]) -> None:
        assert len(met_list) == 6 == len(self.tools), f"Tools: {self.tools}"
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
    new_tool: wx.ToolBarToolBase
    folder_tool: wx.ToolBarToolBase
    edit_tools: list[wx.ToolBarToolBase]
    toolbar: wx.ToolBar
    main_panel: Union[wx.BoxSizer, wx.Panel]
    fileDrop: FileDrop
    entry_list: EntryListPanel
    book: wx.Simplebook  #: The pages to read (`VIEW_PAGE`) and to write (`EDIT_PAGE`).

    # Text
    input_text_field: wx.TextCtrl
    dateLabel: wx.StaticText
    view_label: wx.StaticText
    fix_text_box: wx.TextCtrl

    # Images
    img: wx.StaticBitmap
    image_drop_space: wx.StaticBitmap
    img_prev: wx.StaticBitmap
    prev_img_space: wx.StaticBitmap
    bmp_shown: wx.Bitmap

    prev_img_name = None

    # Boxes
    v_box: wx.BoxSizer

    VIEW_PAGE = 0
    EDIT_PAGE = 1

    text_edit_panel: "TextAndImgPanel"  #: Text input and image to write an entry.
    text_preview_panel: "TextAndImgPanel"  #: Text and image of the shown entry.
    splitter: wx.SplitterWindow

    #: Whether a new entry is written (otherwise the entries are read).
    editing: bool = True

    cdDialog: ChangeDateDialog
    default_img_drop: str
    default_img: str
    imgLoaded: bool

    @staticmethod
    def date_txt(dt: wx.DateTime) -> str:
        return tr("main.date_line", date=format_date_time(dt))

    @staticmethod
    def working_dir_txt() -> str:
        return tr("main.working_dir", path=story_time.util.data_path)

    def set_date_txt(self, dt: wx.DateTime = None) -> None:
        """Sets the text in the date textbox."""
        if dt is None:
            dt = self.cdDialog.dt
        self.dateLabel.SetLabelText(self.date_txt(dt))

    def set_folder_txt(self) -> None:
        """Shows the data folder in the tooltip of the folder tool."""
        self.toolbar.SetToolShortHelp(
            self.folder_tool.Id,
            ToolbarPanel.tool_help("toolbar.folder", "Ctrl+O", self.working_dir_txt()),
        )

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
        self,
        e: Any,
        _diag_fun: Callable = None,
        _photo_fun: Callable = None,
        _no_cam_fun: Callable = None,
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
        try:
            sDiag = SelfieDialog()
        except NoWebcamError:
            md = CustomMessageDialog(
                tr("message.no_webcam.text"),
                tr("message.no_webcam.title"),
                self,
                cancel_only=True,
                cancel_label=tr("common.ok"),
            )
            if _no_cam_fun is not None:
                wx.CallAfter(_no_cam_fun, md)
            md.ShowModal()
            return
        if _diag_fun is not None:
            wx.CallAfter(_diag_fun, sDiag)
        sDiag.ShowModal()
        sDiag.Destroy()
        img = sDiag.taken_img

        # Save the image and show it in the preview
        if img is not None:
            curr_dt = wx.DateTime.Now()
            f_name = get_img_name_from_time(curr_dt) + "_Self.png"
            f_path = os.path.join(get_temp_folder(), f_name)
            cv2.imwrite(f_path, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.fileDrop.loadedFile = f_path
            self.set_img_with_date(f_path, curr_dt)

    @staticmethod
    def toggle_prev_img(_: Any) -> None:
        """Toggles the preview image."""
        print("Toggling")
        pass

    def check_if_discard_changes(
        self, _deb_fun: Callable = None, only_image: bool = False
    ) -> int:
        """Checks whether there is unsaved info.

        Args:
            _deb_fun: Function to call when the dialog pops up. For testing.
            only_image: Whether only a loaded image counts as unsaved info.

        Returns 0 if there is None, 1 if it may be discarded
        and -1 if the user wants to keep it."""
        textStr = self.input_text_field.GetValue()
        if self.imgLoaded or (textStr != "" and not only_image):
            if only_image:
                msg = tr("message.discard_image.text")
            elif self.imgLoaded:
                msg = tr("message.discard_text_image.text")
            else:
                msg = tr("message.discard_text.text")
            md = CustomMessageDialog(
                msg,
                tr("common.warning"),
                self,
                ok_label=tr("common.discard"),
                cancel_label=tr("common.keep"),
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

        The written text is kept. Only if an image is loaded, the user is
        warned that it will be lost if he continues.
        """
        discard_int = self.check_if_discard_changes(_deb_fun, only_image=True)
        if discard_int == -1:
            tog = self.photoTool.IsToggled()
            self.toolbar.ToggleTool(self.photoTool.Id, not tog)
            return -1

        # Toggle the showing of the Image (drop space)
        if self.image_drop_space.IsShown():
            if discard_int == 1:
                # The time was taken from the image.
                self.set_date_to_now()
            self.removeImg()
            self.imgLoaded = False
            self.image_drop_space.Hide()
        else:
            self.image_drop_space.Show()

        # Update the layout
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
                tr("message.no_text.text"),
                tr("message.no_text.title"),
                self,
                cancel_only=True,
                cancel_label=tr("common.ok"),
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
                    tr("message.no_image.text"),
                    tr("message.no_image.title"),
                    self,
                    cancel_only=True,
                    cancel_label=tr("common.ok"),
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
        self.reload_entries()

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
        self.set_folder_txt()
        create_xml_and_img_folder(files_path)
        self.set_date_to_now()
        self.reload_entries()
        self.entry_list.clear_selection()
        if not self.editing:
            self.show_entry(None)

    def OnX(self, _: Any, _deb_fun: Callable = None) -> None:
        """Called when the X is clicked to close.

        Also if self.Close() is called."""
        if self.check_if_discard_changes(_deb_fun) != -1:
            self.Cleanup(None)

    def Cleanup(self, _: Any) -> None:
        """Cleanup, should always be called when app is closed."""
        self.cdDialog.Destroy()
        save_data_folder()
        remove_temp_folder()
        self.Destroy()

    def set_date_to_now(self) -> None:
        """Updates the date and time to now."""
        self.update_date(wx.DateTime.Now())

    def update_date(self, new_date: wx.DateTime = None) -> None:
        """Updates the date to specified datetime and shows it."""
        if new_date is not None:
            self.cdDialog.dt = new_date
        self.set_date_txt()
        self.Layout()

    def reload_entries(self) -> None:
        """Loads all entries from the files and shows them in the list."""
        self.entry_list.set_entries(load_all_entries())

    def show_entry(self, entry: Optional[Entry]) -> None:
        """Shows the entry on the page to read, nothing if `entry` is None."""
        if entry is None:
            self.view_label.SetLabel(tr("main.view.nothing_selected"))
            self.fix_text_box.SetValue("")
            self.rem_prev_img()
        else:
            self.view_label.SetLabel(
                format_date_time(datetime_to_wx_datetime(entry.date_time))
            )
            self.fix_text_box.SetValue(entry.text)
            img_path = (
                os.path.join(story_time.util.img_folder, entry.photo)
                if entry.photo
                else None
            )
            if img_path is not None and os.path.isfile(img_path):
                self.prev_img_name = img_path
                self.set_prev_img(img_path)
            else:
                self.rem_prev_img()
        self.layout_all()

    def set_editing(self, editing: bool) -> None:
        """Switches between writing a new entry and reading the entries."""
        self.editing = editing
        self.book.ChangeSelection(self.EDIT_PAGE if editing else self.VIEW_PAGE)
        self.Layout()
        self.toolbar.ToggleTool(self.new_tool.Id, editing)
        for tool in self.edit_tools:
            self.toolbar.EnableTool(tool.Id, editing)
        if editing:
            self.entry_list.clear_selection()
            self.input_text_field.SetFocus()
        else:
            self.show_entry(self.entry_list.selected_entry())
        self.resized_layout()

    def reset_draft(self) -> None:
        """Throws away the text, the image, the chosen time and the photo mode."""
        self.removeImg()
        self.remove_written_text()
        if self.image_drop_space.IsShown():
            self.image_drop_space.Hide()
        self.toolbar.ToggleTool(self.photoTool.Id, False)

    def leave_editing(self, _deb_fun: Callable = None) -> bool:
        """Goes back to reading, asks first if there is something unsaved.

        Returns whether it was left.
        """
        if self.check_if_discard_changes(_deb_fun) == -1:
            return False
        self.reset_draft()
        self.set_editing(False)
        return True

    def OnNew(self, _: Any, _deb_fun: Callable = None) -> None:
        """Handles the tool to write a new entry, which can also leave it again."""
        if self.toolbar.GetToolState(self.new_tool.Id):
            self.set_editing(True)
        elif not self.leave_editing(_deb_fun):
            self.toolbar.ToggleTool(self.new_tool.Id, True)

    def on_entry_selected(self, entry: Entry, _deb_fun: Callable = None) -> None:
        """Called if the user selects an entry in the list."""
        if self.editing and not self.leave_editing(_deb_fun):
            self.entry_list.clear_selection()
        else:
            self.show_entry(entry)

    def layout_all(self) -> None:
        """Lays out the frame and the panels with the texts and the images.

        Showing or hiding an image does not lay out the panels around it.
        """
        self.Layout()
        for panel in (self.text_edit_panel, self.text_preview_panel):
            panel.Layout()
            panel.GetParent().Layout()

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
        self.cdDialog = ChangeDateDialog(None)
        icon = wx.Icon()
        icon.CopyFromBitmap(
            wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY)
        )
        self.SetIcon(icon)
        files_path = get_data_folder()
        update_folder(files_path)
        print("util.img_folder", util.img_folder)
        self.imgLoaded = False
        self.InitUI()
        self.SetSize((1000, 720))
        self.splitter.SetSashPosition(SIDEBAR_WIDTH)  # It has to follow the size
        self.SetTitle(tr("app.title"))
        self.Center()

    def toggle_new_entry(self) -> None:
        """Same as clicking the tool to write a new entry."""
        tool_id = self.new_tool.Id
        self.toolbar.ToggleTool(tool_id, not self.toolbar.GetToolState(tool_id))
        self.OnNew(None)

    def toggle_photo_mode(self) -> None:
        """Same as clicking the photo tool: toggles it and changes the mode."""
        tool_id = self.photoTool.Id
        self.toolbar.ToggleTool(tool_id, not self.toolbar.GetToolState(tool_id))
        self.OnPhoto(None)

    def on_key(self, event: wx.KeyEvent) -> None:
        """Handles the keyboard shortcuts, passes on all other keys."""
        # The cursor keys are needed to move in the text and in the list
        in_text = isinstance(wx.Window.FindFocus(), (wx.TextCtrl, wx.TreeCtrl))
        action = shortcut_for(
            event.GetKeyCode(),
            event.CmdDown(),
            event.AltDown(),
            event.ShiftDown(),
            in_text,
        )
        if action is None:
            event.Skip()
            return

        # Only the writing tools are needed to write, just like the toolbar
        writing_only = {"save", "photo", "date", "selfie"}
        if action in writing_only and not self.editing:
            return

        handlers = {
            "new": self.toggle_new_entry,
            "save": lambda: self.OnSave(None),
            "photo": self.toggle_photo_mode,
            "date": lambda: self.OnChangeDate(None),
            "folder": lambda: self.OnChangeDir(None),
            "selfie": lambda: self.OnSelfie(None),
            "quit": self.Close,
            # The list has the newest entry on top, so older ones are further down
            "prev": lambda: not self.editing and self.entry_list.select_adjacent(1),
            "next": lambda: not self.editing and self.entry_list.select_adjacent(-1),
        }
        handlers[action]()

    def InitUI(self) -> None:

        # Setup toolbar
        met_list: list = [
            self.OnNew,
            self.OnSave,
            self.OnPhoto,
            self.OnChangeDate,
            self.OnChangeDir,
            self.OnSelfie,
        ]
        tool_panel = ToolbarPanel(self, bg_col=header_col)
        tool_panel.bind_tools(met_list)
        self.photoTool = tool_panel.photoTool
        self.new_tool = tool_panel.new_tool
        self.folder_tool = tool_panel.folder_tool
        self.edit_tools = tool_panel.edit_tools
        self.toolbar = tool_panel.toolbar

        # Left the list of the entries, right the page to read or write one
        splitter = self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.entry_list = EntryListPanel(splitter, self.on_entry_selected)
        right = wx.Panel(splitter)
        self.book = wx.Simplebook(right)

        # Page to read an entry
        view_page = wx.Panel(self.book)
        view_header = TextLinePanel(
            view_page,
            text="",
            center_text=True,
            bg_col=but_bg_col,
            text_col=bar_text_col,
        )
        self.view_label = view_header.stat_text
        text_preview = TextAndImgPanel(
            view_page, editable=False, bg_col=text_bg_col, frame=self
        )
        text_preview.SetMinSize((200, 200))
        self.text_preview_panel = text_preview
        self.text_prev_sizer = text_preview.GetSizer()
        self.fix_text_box = text_preview.text_box
        self.prev_img_space = text_preview.img
        self.prev_img_space.Bind(wx.EVT_LEFT_DOWN, self.on_prev_image_clicked)
        view_box = wx.BoxSizer(wx.VERTICAL)
        view_box.Add(view_header, 0, LR_EXPAND)
        view_box.Add(text_preview, 1, LR_EXPAND)
        view_page.SetSizer(view_box)

        # Page to write an entry
        edit_page = wx.Panel(self.book)
        time_text = TextLinePanel(
            edit_page,
            text=tr("main.date_line", date="12.12.1212, 23:12:55"),
            center_text=True,
            bg_col=but_bg_col,
            text_col=bar_text_col,
        )
        self.dateLabel = time_text.stat_text
        text_edit = TextAndImgPanel(
            edit_page, editable=True, drop_tgt=True, bg_col=text_bg_col, frame=self
        )
        text_edit.SetMinSize((200, 200))
        self.text_edit_panel = text_edit
        self.fileDrop = text_edit.fileDrop
        self.image_drop_space = text_edit.img
        self.image_drop_space.Bind(wx.EVT_LEFT_DOWN, self.on_taken_image_clicked)
        self.input_text_sizer = text_edit.GetSizer()
        self.input_text_field = text_edit.text_box
        edit_box = wx.BoxSizer(wx.VERTICAL)
        edit_box.Add(time_text, 0, LR_EXPAND)
        edit_box.Add(text_edit, 1, LR_EXPAND)
        edit_page.SetSizer(edit_box)

        # The order of the pages is given by `VIEW_PAGE` and `EDIT_PAGE`
        self.book.AddPage(view_page, "")
        self.book.AddPage(edit_page, "")
        right_box = wx.BoxSizer(wx.VERTICAL)
        right_box.Add(self.book, 1, wx.EXPAND)
        right.SetSizer(right_box)

        splitter.SplitVertically(self.entry_list, right, SIDEBAR_WIDTH)
        splitter.SetMinimumPaneSize(220)

        # Put it all together
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(tool_panel, 0, LR_EXPAND)
        box.Add(splitter, 1, wx.EXPAND)
        box.Fit(self)
        self.v_box = box
        self.main_panel = box
        self.SetSizer(box)

        # Prepare UI
        self.set_date_txt()
        self.set_folder_txt()
        self.reload_entries()
        self.set_editing(True)
        self.Bind(wx.EVT_CLOSE, self.OnX)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)

        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        self.SetMinSize((700, 500))

    def on_resize(self, _: Any) -> None:
        self.resized = True  # set dirty
        self.Layout()

    @staticmethod
    def image_size(area: wx.Size) -> int:
        """The edge length of an image next to a text in the given area.

        It fits into the height, leaves most of the width to the text and is not
        larger than `MAX_IMAGE_SIZE`. Returns 0 if the area is too small.
        """
        size = min(area[1], area[0] // 3, MAX_IMAGE_SIZE) - 30
        return size if size > 0 else 0

    def OnIdle(self, _: Any) -> None:
        if self.resized:
            lf = self.fileDrop.loadedFile
            img_size = self.image_size(self.input_text_sizer.Size)
            if img_size > 0:
                set_img = self.default_img_drop if lf is None else lf
                self.image_drop_space.SetBitmap(getImageToShow(set_img, img_size))

            if self.prev_img_name is not None:
                img_size = self.image_size(self.text_prev_sizer.Size)
                if img_size > 0:
                    self.prev_img_space.SetBitmap(
                        getImageToShow(self.prev_img_name, img_size)
                    )

            self.layout_all()
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
