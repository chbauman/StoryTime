"""The dialogs of the app.

Includes `WxDialogs`, which asks the user with these dialogs when the controller
needs something, see `controller.Dialogs`.
"""

import os
import sys
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Callable, Optional

import cv2
import wx
import wx.adv

from story_time.controller import NoWebcamError
from story_time.texts import tr
from story_time.util import (
    button_f_info,
    datetime_to_wx_datetime,
    dialog_f_info,
    get_image_to_show,
    text_bg_col,
    wx_datetime_to_datetime,
)


def ask_for_dir() -> str:
    """Asks the user to select a directory, returns an empty string if canceled."""
    flags = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
    dialog = wx.DirDialog(None, tr("dialog.choose_dir"), "", flags)
    dialog.ShowModal()
    path = dialog.GetPath()
    dialog.Destroy()
    return path


class PhotoShow(wx.Dialog):
    okay: bool = False
    resized = False

    f_name: str

    def __init__(self, parent: wx.Frame, f_name: str) -> None:
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
        self.SetTitle(tr("dialog.photo_show.title"))
        wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        self.f_name = f_name
        b = get_image_to_show(f_name)
        self.image_ctrl = wx.StaticBitmap(self, wx.ID_ANY, b)
        self.v_box.Add(self.image_ctrl, 0, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(self.v_box)

        self.SetBackgroundColour(text_bg_col)
        self.Size = wx.Size(500, 500)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)

    def on_size(self, _: Any) -> None:
        self.resized = True  # set dirty

    def on_idle(self, _: Any) -> None:
        if self.resized:
            # take action if the dirty flag is set
            self.Layout()
            s = self.v_box.Size
            self.image_ctrl.SetBitmap(get_image_to_show(self.f_name, s[1], width=s[0]))
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
        shoot_fun: Optional[Callable] = None,
        cancel_fun: Optional[Callable] = None,
    ) -> None:
        """Layout setup, to be called in self.init_ui."""
        if shoot_fun is None:
            shoot_fun = self.on_take_pic
        if cancel_fun is None:
            cancel_fun = self.on_close

        # Buttons
        shoot_button = wx.Button(self, label=shoot_label)
        # shoot_button.SetBackgroundColour(but_bg_col)
        shoot_button.Bind(wx.EVT_BUTTON, shoot_fun)
        cancel_button = wx.Button(self, label=cancel_label)
        cancel_button.Bind(wx.EVT_BUTTON, cancel_fun)
        # cancel_button.SetBackgroundColour(but_bg_col)
        shoot_button.SetFont(wx.Font(button_f_info))
        cancel_button.SetFont(wx.Font(button_f_info))

        # Layout
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        h_box.Add(shoot_button)

        self.setup_v_box(h_box, cancel_button, pnl)

    def on_take_pic(self, e: Any) -> None:
        pass

    def on_close(self, e: Any) -> None:
        pass


class CustomMessageDialog(TwoButtonDialogBase):
    okay: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        title: Optional[str] = None,
        *args: Any,
        cancel_only: bool = False,
        ok_label: Optional[str] = None,
        cancel_label: Optional[str] = None,
        **kw: Any,
    ) -> None:
        super().__init__(*args, **kw)
        title = tr("dialog.message.title") if title is None else title
        ok_label = tr("common.ok") if ok_label is None else ok_label
        cancel_label = tr("common.cancel") if cancel_label is None else cancel_label
        self.SetTitle(title)
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        if message is not None:
            st_msg = wx.StaticText(self, -1, message)
            st_msg.SetFont(wx.Font(dialog_f_info))
            # st_msg.SetBackgroundColour(green)
            self.v_box.Add(st_msg, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(self.v_box)

        if cancel_only:
            h_box = wx.BoxSizer(wx.HORIZONTAL)
            cancel_butt = wx.Button(self, label=cancel_label)
            cancel_butt.Bind(wx.EVT_BUTTON, self.on_ok)
            cancel_butt.SetFont(wx.Font(button_f_info))
            self.setup_v_box(h_box, cancel_butt, pnl)
        else:
            self.setup(pnl, ok_label, cancel_label, self.on_ok, self.on_close)

    def on_ok(self, _: Any) -> None:
        self.okay = True
        self.Close()

    def on_close(self, _: Any) -> None:
        self.Close()


class ChangeDateDialog(TwoButtonDialogBase):
    """Date and Time picker dialog"""

    start_dt: wx.DateTime
    dt: wx.DateTime
    cal: wx.adv.CalendarCtrl
    time_picker: wx.adv.TimePickerCtrl

    #: The date picked with Ok or Now, None if the dialog was canceled.
    picked: Optional[wx.DateTime] = None

    def __init__(
        self, *args: Any, start: Optional[wx.DateTime] = None, **kw: Any
    ) -> None:
        super().__init__(*args, **kw)

        self.set_time_now()
        if start is not None:
            self.dt = start
        self.init_ui()
        self.cal.SetDate(self.dt)

        self.SetSize((400, 400))
        self.SetTitle(tr("dialog.change_date.title"))

    def init_ui(self) -> None:
        pnl = wx.Panel(self)

        # Define UI elements
        top_text = wx.StaticText(self, label=tr("dialog.change_date.heading"))
        top_text.SetFont(wx.Font(dialog_f_info))
        self.cal = wx.adv.CalendarCtrl(self)
        time_txt = wx.StaticText(self, label=tr("dialog.change_date.time") + " ")
        self.time_picker = wx.adv.TimePickerCtrl(self, dt=self.dt)

        # Define extra button
        now_button = wx.Button(self, label=tr("dialog.change_date.now"))
        now_button.Bind(wx.EVT_BUTTON, self.set_now_and_close)
        now_button.SetFont(wx.Font(button_f_info))

        # Define sizer for time
        sbs = wx.BoxSizer(wx.HORIZONTAL)
        sbs.Add(time_txt, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        sbs.Add(self.time_picker, flag=wx.ALL, border=5)

        # Define top-level sizer
        self.v_box = wx.BoxSizer(wx.VERTICAL)
        self.v_box.Add(top_text, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(sbs, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(self.cal, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.v_box.Add(now_button, flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        self.setup(pnl, tr("common.ok"), tr("common.cancel"), self.on_ok, self.on_close)

    def set_time_now(self) -> None:
        """Sets the time to now."""
        self.dt = wx.DateTime.Now()

    def set_now_and_close(self, _: Any) -> None:
        self.set_time_now()
        self.picked = self.dt
        self.on_close(None)

    def get_time(self) -> wx.DateTime:
        time_tuple = self.time_picker.GetTime()
        dt = self.cal.GetDate()
        dt.SetHour(time_tuple[0])
        dt.SetMinute(time_tuple[1])
        dt.SetSecond(time_tuple[2])
        return dt

    def on_close(self, e: Any) -> None:
        self.Close()

    def on_ok(self, _: Any) -> None:
        """Sets `self.dt` to the current time."""
        self.dt = self.get_time()
        self.picked = self.dt
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
        img_folder: str,
        file_list: Sequence,
        parent: Optional[wx.Frame] = None,
        title: Optional[str] = None,
    ) -> None:
        """
        Args:
            img_folder: The folder with the images.
            file_list: The names of the images in the folder to choose from.
            parent: The parent window.
            title: The title of the dialog.
        """
        title = tr("dialog.same_date.title") if title is None else title
        super().__init__(parent, title=title)

        self.img_folder = img_folder
        self.file_list = file_list
        self.chosen_img_ind: Optional[int] = None
        self.shown_img_ind = 0
        self.n_files = len(file_list)
        self.init_ui()
        self.SetSize((400, 300))
        self.SetTitle(title)

    def init_ui(self) -> None:

        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        self.bmp_shown = self.get_img_at_ind(0)
        self.img = wx.StaticBitmap(self, -1, self.bmp_shown)
        self.v_box.Add(self.img, proportion=0, flag=wx.ALL, border=5)
        self.img.Show()

        # Buttons
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        select_button = wx.Button(self, label=tr("dialog.same_date.select"))
        new_button = wx.Button(self, label=tr("dialog.same_date.new"))

        h_box.Add(select_button)

        if self.n_files > 1:  # No next / previous if there is only one
            self.next_button = wx.Button(self, label=tr("common.next"))
            self.prev_button = wx.Button(self, label=tr("common.previous"))
            self.prev_button.Disable()
            h_box.Add(self.prev_button)
            h_box.Add(self.next_button)
            self.next_button.Bind(wx.EVT_BUTTON, self.on_next)
            self.prev_button.Bind(wx.EVT_BUTTON, self.on_prev)

        self.setup_v_box(h_box, new_button, pnl)
        select_button.Bind(wx.EVT_BUTTON, self.on_select)

        new_button.Bind(wx.EVT_BUTTON, self.on_new)

    def get_img_at_ind(self, ind: int) -> wx.Bitmap:
        pth = os.path.join(self.img_folder, self.file_list[ind])
        return get_image_to_show(pth, 100, border=5)

    def update_img(self) -> None:
        ind = self.shown_img_ind
        img_to_show = self.get_img_at_ind(ind)
        self.img.SetBitmap(img_to_show)

    def on_next(self, _: Any) -> None:
        self.shown_img_ind += 1
        if self.shown_img_ind == self.n_files - 1:
            self.next_button.Disable()
        if self.shown_img_ind == 1:
            self.prev_button.Enable()
        self.update_img()

    def on_prev(self, _: Any) -> None:
        self.shown_img_ind -= 1
        if self.shown_img_ind == 0:
            self.prev_button.Disable()
        if self.shown_img_ind == self.n_files - 2:
            self.next_button.Enable()
        self.update_img()

    def on_select(self, _: Any) -> None:
        self.chosen_img_ind = self.shown_img_ind
        self.Close()

    def on_close(self, _: Any) -> None:
        self.Close()

    def on_new(self, _: Any) -> None:
        self.chosen_img_ind = -1  # This means new
        self.Close()


class ShowCapture(wx.Panel):
    """Panel that shows the content recorded by the webcam."""

    def __init__(self, parent: Any, capture: Any, fps: int = 25) -> None:

        # Capture first frame to get size
        self.capture = capture
        ret, frame = self.capture.read()
        if not ret or frame is None:
            raise NoWebcamError("Could not read from the webcam.")
        height, width = frame.shape[:2]
        self.h_by_w = height / width
        self.win_size = (300, round(self.h_by_w * 300))

        wx.Panel.__init__(self, parent, wx.ID_ANY, (0, 0), self.win_size)
        parent.SetSize(self.win_size)

        self.h, self.w = self.win_size
        frame = cv2.cvtColor(cv2.resize(frame, self.win_size), cv2.COLOR_BGR2RGB)
        self.bmp = wx.Bitmap.FromBuffer(self.h, self.w, frame)

        self.timer = wx.Timer(self)
        self.timer.Start(round(1000.0 / fps))

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_TIMER, self.next_frame)

    def get_curr_frame(self) -> Any:
        ret, frame = self.capture.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def on_paint(self, _: Any) -> None:
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def next_frame(self, _: Any) -> None:
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
        self,
        parent: Optional[wx.Frame] = None,
        img: Optional[Any] = None,
        title: Optional[str] = None,
    ) -> None:
        title = tr("dialog.accept_photo.title") if title is None else title
        super().__init__(parent, title=title)

        if img is not None:
            self.set_img(img)
        self.SetSize((400, 350))
        self.SetTitle(title)
        self.accepted = False

    def init_ui(self) -> None:
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        assert self.taken_img is not None
        height, width, _channels = self.taken_img.shape
        self.orig_img = self.taken_img
        height, width = (300, int(height / width * 300))
        new_size = height, width
        self.taken_img = cv2.resize(self.taken_img, new_size)
        bmp = wx.Bitmap.FromBuffer(height, width, self.taken_img.tobytes())
        bmp = wx.StaticBitmap(self, -1, bmp, size=new_size)
        self.v_box.Add(
            bmp, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border=5
        )

        self.setup(
            pnl, tr("dialog.accept_photo.accept"), tr("dialog.accept_photo.discard")
        )

    def set_img(self, img: str) -> None:
        self.taken_img = img
        self.init_ui()

    def on_take_pic(self, e: Any) -> None:
        self.accepted = True
        self.Close()

    def on_close(self, e: Any) -> None:
        self.Close()


class SelfieDialog(TwoButtonDialogBase):
    """Dialog that lets you take a picture with the webcam."""

    taken_img = None
    dt_taken = None

    _vid_capture: cv2.VideoCapture
    _img_cap: ShowCapture

    accept_diag: AcceptPhoto

    def __init__(self, parent: Any = None, title: Optional[str] = None) -> None:
        title = tr("dialog.selfie.title") if title is None else title
        super().__init__(parent, title=title)

        try:
            self.init_ui()
        except NoWebcamError:
            self.Destroy()
            raise
        self.SetSize((400, 350))
        self.SetTitle(title)

        self.accept_diag = AcceptPhoto(None, img=None)

    def init_ui(self) -> None:
        pnl = wx.Panel(self)
        self.v_box = wx.BoxSizer(wx.VERTICAL)

        # Current Image
        # DirectShow is only available on Windows, let OpenCV choose otherwise.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self._vid_capture = cv2.VideoCapture(0, backend)
        try:
            self._img_cap = ShowCapture(self, self._vid_capture)
        except NoWebcamError:
            self._vid_capture.release()
            raise
        self.v_box.Add(
            self._img_cap,
            proportion=0,
            flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL,
            border=5,
        )
        self._img_cap.Show()
        self.setup(pnl, tr("dialog.selfie.shoot"), tr("common.cancel"))

    def on_take_pic(self, e: Any) -> None:
        """Takes a picture with the webcam.

        Captures the current frame and
        shows the Dialog that lets the user accept the photo or decide
        to take another one.
        """
        curr_f: Any = self._img_cap.get_curr_frame()
        self.accept_diag.set_img(curr_f)
        self.accept_diag.ShowModal()
        if self.accept_diag.accepted:
            self.taken_img = self.accept_diag.orig_img
            self.release_cap()

    def release_cap(self, _: Any = None) -> None:
        self._vid_capture.release()
        cv2.destroyAllWindows()
        self.accept_diag.Destroy()
        self.Close()

    def on_close(self, e: Any) -> None:
        self.release_cap()


class WxDialogs:
    """Asks the user with the dialogs of the app, implements `controller.Dialogs`."""

    def __init__(self, parent: Optional[wx.Window] = None) -> None:
        self.parent = parent

    def ask_folder(self) -> Optional[str]:
        return ask_for_dir() or None

    def confirm(self, text: str, title: str, ok_label: str, cancel_label: str) -> bool:
        dialog = CustomMessageDialog(
            text, title, self.parent, ok_label=ok_label, cancel_label=cancel_label
        )
        dialog.SetSize((400, 300))
        dialog.ShowModal()
        dialog.Destroy()
        return dialog.okay

    def info(self, text: str, title: str) -> None:
        dialog = CustomMessageDialog(
            text, title, self.parent, cancel_only=True, cancel_label=tr("common.ok")
        )
        dialog.ShowModal()
        dialog.Destroy()

    def choose_image(self, img_folder: str, files: list[str]) -> Optional[int]:
        dialog = PhotoWithSameDateExistsDialog(img_folder, files)
        dialog.ShowModal()
        dialog.Destroy()
        return dialog.chosen_img_ind

    def pick_image_file(self) -> Optional[str]:
        wildcard = "|".join(
            [
                f"{tr('dialog.image_files')}|*.jpg;*.jpeg;*.png;*.bmp",
                f"{tr('dialog.all_files')}|*",
            ]
        )
        with wx.FileDialog(
            self.parent,
            tr("main.upload_image"),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return dialog.GetPath()

    def pick_date(self, start: datetime) -> Optional[datetime]:
        dialog = ChangeDateDialog(self.parent, start=datetime_to_wx_datetime(start))
        dialog.ShowModal()
        picked = dialog.picked
        dialog.Destroy()
        return None if picked is None else wx_datetime_to_datetime(picked)

    def take_selfie(self, save_to: str) -> bool:
        dialog = SelfieDialog()  # Raises NoWebcamError without a webcam
        dialog.ShowModal()
        dialog.Destroy()
        img = dialog.taken_img
        if img is None:
            return False
        os.makedirs(os.path.dirname(save_to), exist_ok=True)
        cv2.imwrite(save_to, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        return True

    def show_photo(self, path: str) -> None:
        dialog = PhotoShow(self.parent, path)
        dialog.ShowModal()
        dialog.Destroy()
