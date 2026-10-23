import os
from contextlib import contextmanager
from datetime import datetime
from unittest import TestCase, skipUnless

import cv2
import wx

import story_time.util
from story_time.util import (
    AcceptPhoto,
    ChangeDateDialog,
    CustomMessageDialog,
    FileDrop,
    NoWebcamError,
    PhotoWithSameDateExistsDialog,
    SelfieDialog,
    ShowCapture,
    TwoButtonDialogBase,
    ask_for_dir,
    datetime_to_wx_datetime,
    format_date_time,
    wx_datetime_to_datetime,
)
from tests.helpers import SAMPLE_IMG_DIR, img_dir, use_data_dir, xml_dir  # noqa: F401


def _webcam_available() -> bool:
    cap = cv2.VideoCapture(0)
    try:
        return cap.isOpened() and cap.read()[0]
    finally:
        cap.release()


HAS_WEBCAM = _webcam_available()


class _NoFrameCapture:
    """Mimics a webcam that does not deliver any frames."""

    @staticmethod
    def read():
        return False, None


@contextmanager
def create_app():
    a = wx.App()
    f = wx.Frame()
    f.Create(None)
    yield f
    a.Destroy()


@contextmanager
def replace_dir_ask(new_ask_fun):
    ask_fun = story_time.util.ask_for_dir
    story_time.util.ask_for_dir = new_ask_fun
    yield
    story_time.util.ask_for_dir = ask_fun


class TestUtil(TestCase):
    def test_wx_datetime_conversion(self):
        dt = datetime(2020, 12, 2, 5, 31, 7)
        wx_dt = datetime_to_wx_datetime(dt)
        assert (wx_dt.GetDay(), wx_dt.GetMonth(), wx_dt.GetYear()) == (2, 11, 2020)
        assert wx_dt.IsEqualTo(wx.DateTime(2, 11, 2020, 5, 31, 7))
        assert wx_datetime_to_datetime(wx_dt) == dt

    def test_format_dt(self):
        res = format_date_time(datetime(2020, 12, 2, 5, 31))
        assert ",".join(res.split(",")[1:]) == " 2.12.2020, Time: 05:31:00"
        # The weekday comes from wx
        assert res.split(",")[0] == wx.DateTime.GetWeekDayName(wx.DateTime.Wed)


def init_app():
    return wx.App(), wx.Frame()


def run_diag(dlg, fun, destroy: bool = True):
    wx.CallAfter(fun)
    dlg.ShowModal()
    if destroy and dlg:  # The dialog may have destroyed itself when closing.
        dlg.Destroy()


class TestGUIElements(TestCase):
    def test_dir_asking(self):
        def dummy_fun(_):
            pass

        with create_app():
            fol = ask_for_dir(dummy_fun, show=False)
            assert fol is None or fol == ""

    def test_message_dlg(self):
        def abort(d):
            d.OnClose(None)

        def ok(d):
            d.OnOK(None)

        with create_app() as f:
            md = CustomMessageDialog("Message", "title", f)
            wx.CallAfter(abort, md)
            assert md.ShowModal() == wx.ID_CANCEL

            print(f"Cancel: {wx.ID_CANCEL}")
            print(f"Ok: {wx.ID_OK}")
            print(f"Cancel: {wx.ID_YES}")

            md = CustomMessageDialog("Message", "title", f)
            wx.CallAfter(ok, md)
            assert md.ShowModal() == wx.ID_CANCEL

            md = CustomMessageDialog("Message", "title", f, cancel_only=True)
            wx.CallAfter(ok, md)
            ans = md.ShowModal()
            assert ans == wx.ID_CANCEL

    def test_file_drop(self):
        class DummyFrame:
            def set_img_with_date(self, *args, **kwargs):
                pass

        d_frame = DummyFrame()
        fd = FileDrop(None, d_frame)
        assert fd.OnDropFiles(0, 0, ["test/IMG_20201202_053100.jpg"])
        assert fd.OnDropFiles(0, 0, ["test/IMG_20201202_053100.jpg", "fail"])
        assert not fd.OnDropFiles(0, 0, ["fail"])

    def test_dialog_base(self):
        with create_app():
            d = TwoButtonDialogBase()
            d.OnTakePic(None)
            d.OnClose(None)

    def test_change_date_dialog(self):
        with create_app() as f:
            dlg = ChangeDateDialog(f)

            def clickOK():
                dlg.OnOK(None)

            run_diag(dlg, clickOK)

            def cancel():
                dlg.OnClose(None)

            run_diag(dlg, cancel)

    def test_photo_exists_dialog(self):
        with create_app():
            img_list = [
                os.path.join(SAMPLE_IMG_DIR, f)
                for f in ["Entwurf.jpg", "calendar_icon.png"]
            ]

            # A destroyed dialog cannot be shown again, so create a new one each time.
            photo_dlg = PhotoWithSameDateExistsDialog(img_list)

            def test_1():
                photo_dlg.OnNext(None)
                photo_dlg.OnPrev(None)
                photo_dlg.OnSelect(None)

            run_diag(photo_dlg, test_1)
            assert photo_dlg.chosenImgInd == 0

            photo_dlg = PhotoWithSameDateExistsDialog(img_list)

            def test_2():
                photo_dlg.OnClose(None)

            run_diag(photo_dlg, test_2)

            photo_dlg = PhotoWithSameDateExistsDialog(img_list)

            def test_3():
                photo_dlg.OnNew(None)

            run_diag(photo_dlg, test_3)
            assert photo_dlg.chosenImgInd == -1

    def test_no_webcam_error(self):
        with create_app():
            with self.assertRaises(NoWebcamError):
                ShowCapture(None, _NoFrameCapture())

    @skipUnless(HAS_WEBCAM, "No webcam available.")
    def test_selfie_dialog(self):
        with create_app():
            photo_dlg = SelfieDialog()

            def test_1():
                def inner():
                    photo_dlg.accept_diag.OnTakePic(None)

                photo_dlg.OnTakePic(None, inner)

            run_diag(photo_dlg, test_1)
            assert photo_dlg.taken_img is not None

            photo_dlg = SelfieDialog()

            def test_2():
                def inner():
                    photo_dlg.accept_diag.OnClose(None)

                photo_dlg.OnTakePic(None, inner)
                photo_dlg.OnClose(None)

            run_diag(photo_dlg, test_2)
            assert photo_dlg.taken_img is None

    def test_accept_photo(self):
        with create_app():
            img = cv2.imread(os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg"), 0)
            img2 = cv2.merge((img, img, img))
            AcceptPhoto(img=img2)

    pass
