"""The main window.

Inspired by: ZetCode wxPython tutorial, www.zetcode.com
"""

import os
from datetime import datetime
from typing import Any, Callable, ClassVar, NamedTuple, Optional, Union

import wx

from story_time.controller import Dialogs, DiaryController
from story_time.dialogs import WxDialogs
from story_time.entries import Entry, group_by_month
from story_time.shortcuts import shortcut_for
from story_time.texts import tr
from story_time.util import (
    FileDrop,
    bar_text_col,
    but_bg_col,
    datetime_to_wx_datetime,
    format_date_time,
    get_image_to_show,
    header_col,
    header_f_info,
    header_text_col,
    icon_path,
    resource_filename,
    scale_bitmap,
    text_bg_col,
)

LR_EXPAND = wx.LEFT | wx.RIGHT | wx.EXPAND
SIDEBAR_WIDTH = 340  #: Initial width of the list of the entries.
MAX_IMAGE_SIZE = 400  #: Maximum edge length of the shown images in pixels.
UNDO_SECONDS = 8  #: How long a discard can be undone.
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
        on_image: Optional[Callable[[str], bool]] = None,
        on_remove_image: Optional[Callable[[], object]] = None,
    ):
        """
        Args:
            parent: The parent window.
            editable: Whether it is the text input (otherwise a read-only text).
            drop_tgt: Whether the image is a drop target for image files.
            bg_col: The background color.
            on_image: Called with the path of an image dropped on the image area,
                returns whether it was accepted.
            on_remove_image: Called when the button to remove the image is
                clicked, only used with `drop_tgt`.
        """
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)

        # The image
        img_name = f"default_img{'_txt' if drop_tgt else ''}.png"
        self.default_img = resource_filename(f"Icons/{img_name}")

        self.bmp_shown = get_image_to_show(self.default_img)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        if drop_tgt:
            self.img.Hide()
            self.file_drop = FileDrop(self.img, on_image or (lambda _: False))
            self.img.SetDropTarget(self.file_drop)
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

        exp_all = wx.EXPAND | wx.ALL
        h_box_3 = wx.BoxSizer(wx.HORIZONTAL)

        if drop_tgt:
            self.remove_image_button = wx.Button(self, label=tr("main.remove_image"))
            self.remove_image_button.Hide()
            self.remove_image_button.Bind(
                wx.EVT_BUTTON, lambda _: (on_remove_image or (lambda: None))()
            )
            img_box = wx.BoxSizer(wx.VERTICAL)
            img_box.Add(self.img, 0, wx.ALIGN_CENTER_HORIZONTAL)
            img_box.Add(self.remove_image_button, 0, wx.ALIGN_CENTER | wx.TOP, 5)
            h_box_3.Add(img_box, proportion=1, flag=wx.ALL | wx.ALIGN_TOP, border=5)
        else:
            h_box_3.Add(self.img, proportion=1, flag=wx.ALL | wx.ALIGN_TOP, border=5)
        h_box_3.Add(self.text_box, proportion=3, flag=exp_all, border=5)

        box.Add(h_box_3, 1, exp_all, 5)
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
    """List of entries, grouped by month, with a search field.

    It only shows the entries it is given, the search and the selection of the
    user are passed on.
    """

    def __init__(
        self,
        parent: wx.Window,
        on_select: Callable[[Entry], None],
        on_query: Callable[[str], None],
        bg_col: wx.Colour = text_bg_col,
    ):
        """
        Args:
            parent: The parent window.
            on_select: Called with the entry when the user selects one.
            on_query: Called with the text when the user changes the search.
            bg_col: The background color.
        """
        wx.Panel.__init__(self, parent)
        self.on_select = on_select
        self.on_query = on_query
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

        self.search.Bind(wx.EVT_TEXT, lambda _: self.on_query(self.search.GetValue()))
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)

    def set_entries(
        self, shown: list[Entry], total: int, selected: Optional[Entry] = None
    ) -> None:
        """Shows the entries, newest first, and selects `selected` if it is one.

        Args:
            shown: The entries to show.
            total: The number of all entries, also the ones not shown.
            selected: The entry to select.
        """
        searching = bool(self.search.GetValue().strip())
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
                if n == 0 or searching:
                    self.tree.Expand(month_item)
            for entry, item in self.shown:
                if entry == selected:
                    self.tree.SelectItem(item)
                    self.tree.EnsureVisible(item)
            self.tree.Thaw()
        finally:
            self._notify = True

        if total == 0:
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

    def _on_tree_selection(self, _: Any) -> None:
        entry = self.selected_entry()
        if self._notify and entry is not None:
            self.on_select(entry)


class ToolSpec(NamedTuple):
    """A tool of the toolbar."""

    icon: str  #: The name of the icon file.
    text_key: str  #: The key of the texts of the tool.
    shortcut: str  #: The keyboard shortcut, only shown.
    toggle: bool = False  #: Whether the tool can be toggled.


class ToolbarPanel(wx.Panel):
    tool_list: ClassVar[list[ToolSpec]] = [
        ToolSpec("new_icon.png", "toolbar.new", "Ctrl+N", toggle=True),
        ToolSpec("save_icon.png", "toolbar.save", "Ctrl+S"),
        ToolSpec("photo_icon.png", "toolbar.photo", "Ctrl+P", toggle=True),
        ToolSpec("calendar_icon.png", "toolbar.date", "Ctrl+D"),
        ToolSpec("folder_icon.png", "toolbar.folder", "Ctrl+O"),
        ToolSpec("webcam_icon.png", "toolbar.selfie", "Ctrl+T"),
    ]
    tools: list[wx.ToolBarToolBase]
    photo_tool: Union[Any, wx.ToolBarToolBase]
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
        icon_size = (50, 50)

        self.toolbar.SetToolBitmapSize(icon_size)

        for spec in self.tool_list:
            tool_id = wx.Window.NewControlId()
            icon = scale_bitmap(
                wx.Bitmap(resource_filename(f"Icons/{spec.icon}")), *icon_size
            )
            add_tool = (
                self.toolbar.AddCheckTool if spec.toggle else self.toolbar.AddTool
            )
            tool = add_tool(
                tool_id,
                tr(f"{spec.text_key}.name"),
                icon,
                shortHelp=self.tool_help(spec.text_key, spec.shortcut),
            )
            self.tools.append(tool)

        self.new_tool = self.tools[0]
        self.photo_tool = self.tools[2]
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


class StoryTimeAppUI(wx.Frame):
    """The main window of the app.

    It shows what the `DiaryController` tells it to, see `controller.View`, and
    passes the actions of the user on to the controller, which has all the logic.
    """

    VIEW_PAGE = 0  #: The page to read an entry in `book`.
    EDIT_PAGE = 1  #: The page to write an entry in `book`.

    resized = True

    #: The path of the image of the entry that is written, if there is one.
    draft_image: Optional[str] = None
    #: The path of the image of the entry that is read, if there is one.
    prev_img_name: Optional[str] = None

    def __init__(
        self, parent: Optional[wx.Window] = None, dialogs: Optional[Dialogs] = None
    ) -> None:
        """
        Args:
            parent: The parent window.
            dialogs: How to ask the user, the dialogs of the app by default.
        """
        super().__init__(parent)
        self.default_img_drop = os.path.join(icon_path, "default_img_txt.png")
        icon = wx.Icon()
        icon.CopyFromBitmap(
            wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY)
        )
        self.SetIcon(icon)
        self.init_ui()

        self.controller = DiaryController(self, dialogs or WxDialogs(self))
        if not self.controller.start():  # There is no data folder
            self.Destroy()
            raise SystemExit(0)
        self.SetSize((1000, 720))
        self.splitter.SetSashPosition(SIDEBAR_WIDTH)  # It has to follow the size
        self.SetTitle(tr("app.title"))
        self.Center()

    def init_ui(self) -> None:
        # Setup toolbar
        tool_panel = ToolbarPanel(self, bg_col=header_col)
        tool_panel.bind_tools(
            [
                lambda _: self.controller.set_writing(
                    self.toolbar.GetToolState(self.new_tool.Id)
                ),
                lambda _: self.controller.save(),
                lambda _: self.controller.set_photo_mode(
                    self.toolbar.GetToolState(self.photo_tool.Id)
                ),
                lambda _: self.controller.change_date(),
                lambda _: self.controller.change_folder(),
                lambda _: self.controller.take_selfie(),
            ]
        )
        self.photo_tool = tool_panel.photo_tool
        self.new_tool = tool_panel.new_tool
        self.folder_tool = tool_panel.folder_tool
        self.edit_tools = tool_panel.edit_tools
        self.toolbar = tool_panel.toolbar

        # Left the list of the entries, right the page to read or write one
        splitter = self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.entry_list = EntryListPanel(
            splitter,
            on_select=lambda entry: self.controller.select_entry(entry),
            on_query=lambda query: self.controller.set_query(query),
        )
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
        text_preview = TextAndImgPanel(view_page, editable=False, bg_col=text_bg_col)
        text_preview.SetMinSize((200, 200))
        self.text_preview_panel = text_preview
        self.text_prev_sizer = text_preview.GetSizer()
        self.fix_text_box = text_preview.text_box
        self.prev_img_space = text_preview.img
        self.prev_img_space.Bind(
            wx.EVT_LEFT_DOWN, lambda _: self.controller.show_selected_image()
        )
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
        self.date_label = time_text.stat_text
        text_edit = TextAndImgPanel(
            edit_page,
            editable=True,
            drop_tgt=True,
            bg_col=text_bg_col,
            on_image=lambda path: self.controller.load_image(path),
            on_remove_image=lambda: self.controller.remove_image(),
        )
        text_edit.SetMinSize((200, 200))
        self.text_edit_panel = text_edit
        self.image_drop_space = text_edit.img
        self.image_drop_space.Bind(
            wx.EVT_LEFT_DOWN, lambda _: self.controller.show_draft_image()
        )
        self.input_text_sizer = text_edit.GetSizer()
        self.input_text_field = text_edit.text_box
        self.input_text_field.Bind(
            wx.EVT_TEXT, lambda _: self.controller.dismiss_undo()
        )
        self.remove_image_button = text_edit.remove_image_button
        self.discard_button = wx.Button(edit_page, label=tr("main.discard"))
        self.discard_button.SetToolTip(f"{tr('toolbar.discard.help')} (Esc)")
        self.discard_button.Bind(
            wx.EVT_BUTTON, lambda _: self.controller.discard_draft()
        )
        edit_box = wx.BoxSizer(wx.VERTICAL)
        edit_box.Add(time_text, 0, LR_EXPAND)
        edit_box.Add(text_edit, 1, LR_EXPAND)
        edit_box.Add(self.discard_button, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        edit_page.SetSizer(edit_box)

        # The order of the pages is given by `VIEW_PAGE` and `EDIT_PAGE`
        self.book.AddPage(view_page, "")
        self.book.AddPage(edit_page, "")
        right_box = wx.BoxSizer(wx.VERTICAL)
        right_box.Add(self.book, 1, wx.EXPAND)
        right.SetSizer(right_box)

        # The bar to undo a discard, only shown for a few seconds
        self.undo_bar = wx.Panel(right)
        self.undo_bar.SetBackgroundColour(but_bg_col)
        self.undo_label = wx.StaticText(self.undo_bar, label="")
        self.undo_label.SetForegroundColour(bar_text_col)
        self.undo_button = wx.Button(self.undo_bar, label=tr("undo.undo"))
        self.undo_button.Bind(wx.EVT_BUTTON, lambda _: self.controller.undo_discard())
        undo_box = wx.BoxSizer(wx.HORIZONTAL)
        undo_box.Add(self.undo_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)
        undo_box.Add(self.undo_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        self.undo_bar.SetSizer(undo_box)
        self.undo_bar.Hide()
        self.undo_timer = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, lambda _: self.controller.dismiss_undo(), self.undo_timer
        )
        right_box.Add(self.undo_bar, 0, wx.EXPAND)

        splitter.SplitVertically(self.entry_list, right, SIDEBAR_WIDTH)
        splitter.SetMinimumPaneSize(220)

        # Put it all together
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(tool_panel, 0, LR_EXPAND)
        box.Add(splitter, 1, wx.EXPAND)
        box.Fit(self)
        self.SetSizer(box)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_IDLE, self.on_idle)

        self.SetMinSize((700, 500))

    # ------------------------------------------------- what the user does

    def on_close(self, _: Any) -> None:
        """Called when the X is clicked to close, also by `Close`.

        The window is only closed if there is nothing unsaved or the user agrees.
        """
        if self.controller.request_close():
            self.cleanup()

    def cleanup(self) -> None:
        """cleanup, should always be called when app is closed."""
        self.controller.finish()
        self.Destroy()

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
        else:
            self.controller.run_shortcut(action)

    # -------------------------------------------- what the controller shows

    def get_text(self) -> str:
        return self.input_text_field.GetValue()

    def set_text(self, text: str) -> None:
        # Without the event, which is for what the user types
        self.input_text_field.ChangeValue(text)

    def show_mode(self, editing: bool, photo_mode: bool) -> None:
        self.book.ChangeSelection(self.EDIT_PAGE if editing else self.VIEW_PAGE)
        self.Layout()
        self.toolbar.ToggleTool(self.new_tool.Id, editing)
        self.toolbar.ToggleTool(self.photo_tool.Id, photo_mode)
        # Only the tools to write are needed to write
        for tool in self.edit_tools:
            self.toolbar.EnableTool(tool.Id, editing)
        self.image_drop_space.Show(photo_mode)
        self._show_remove_button()
        if editing:
            self.input_text_field.SetFocus()
        self.resized_layout()

    def show_draft_image(self, path: Optional[str]) -> None:
        self.draft_image = path
        self.image_drop_space.SetBitmap(
            get_image_to_show(self.default_img_drop if path is None else path)
        )
        self._show_remove_button()
        self.resized_layout()

    def _show_remove_button(self) -> None:
        """The button to remove the image is only there if there is one."""
        self.remove_image_button.Show(
            self.draft_image is not None and self.image_drop_space.IsShown()
        )
        self.input_text_sizer.Layout()

    def show_draft_date(self, date_time: datetime) -> None:
        self.date_label.SetLabelText(
            tr("main.date_line", date=format_date_time(date_time))
        )
        self.Layout()

    def show_entry(self, entry: Optional[Entry], image: Optional[str]) -> None:
        if entry is None:
            self.view_label.SetLabel(tr("main.view.nothing_selected"))
            self.fix_text_box.SetValue("")
        else:
            self.view_label.SetLabel(format_date_time(entry.date_time))
            self.fix_text_box.SetValue(entry.text)
        if image is None:
            self.rem_prev_img()
        else:
            self.set_prev_img(image)
        self.layout_all()

    def show_entries(
        self, shown: list[Entry], total: int, selected: Optional[Entry]
    ) -> None:
        self.entry_list.set_entries(shown, total, selected)

    def select_entry(self, entry: Optional[Entry]) -> None:
        if entry is None:
            self.entry_list.clear_selection()
        else:
            self.entry_list.select_entry(entry)

    def show_undo(self, message: Optional[str]) -> None:
        self.undo_timer.Stop()
        if message is not None:
            self.undo_label.SetLabel(message)
            self.undo_timer.StartOnce(int(UNDO_SECONDS * 1000))
        self.undo_bar.Show(message is not None)
        self.undo_bar.GetParent().Layout()
        self.Layout()

    def show_folder(self, path: str) -> None:
        """Shows the data folder in the tooltip of the folder tool."""
        self.toolbar.SetToolShortHelp(
            self.folder_tool.Id,
            ToolbarPanel.tool_help(
                "toolbar.folder", "Ctrl+O", tr("main.working_dir", path=path)
            ),
        )

    def close(self) -> None:
        self.Close()

    # ---------------------------------------------------------------- layout

    def set_prev_img(self, name: str) -> None:
        """Sets an image in the panel to read an entry."""
        self.prev_img_name = name
        self.prev_img_space.SetBitmap(get_image_to_show(name))
        self.prev_img_space.Show()
        self.resized_layout()

    def rem_prev_img(self) -> None:
        """Removes the image of the panel to read an entry by hiding it."""
        self.prev_img_name = None
        self.prev_img_space.Hide()

    def layout_all(self) -> None:
        """Lays out the frame and the panels with the texts and the images.

        Showing or hiding an image does not lay out the panels around it.
        """
        self.Layout()
        for panel in (self.text_edit_panel, self.text_preview_panel):
            panel.Layout()
            panel.GetParent().Layout()

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

    def on_idle(self, _: Any) -> None:
        if self.resized:
            img_size = self.image_size(self.input_text_sizer.Size)
            if img_size > 0:
                set_img = (
                    self.default_img_drop
                    if self.draft_image is None
                    else self.draft_image
                )
                self.image_drop_space.SetBitmap(get_image_to_show(set_img, img_size))

            if self.prev_img_name is not None:
                img_size = self.image_size(self.text_prev_sizer.Size)
                if img_size > 0:
                    self.prev_img_space.SetBitmap(
                        get_image_to_show(self.prev_img_name, img_size)
                    )

            self.layout_all()
            self.resized = False  # reset the flag

    def resized_layout(self) -> None:
        self.on_resize(None)
        self.on_idle(None)
