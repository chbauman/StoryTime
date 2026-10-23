import os
from datetime import datetime
from unittest import TestCase, skipUnless
from unittest.mock import patch

import cv2
import wx

from story_time import dialogs, folders
from story_time.controller import NoWebcamError
from story_time.dialogs import (
    AcceptPhoto,
    ChangeDateDialog,
    CustomMessageDialog,
    PhotoShow,
    PhotoWithSameDateExistsDialog,
    SelfieDialog,
    ShowCapture,
    TwoButtonDialogBase,
    WxDialogs,
)
from story_time.images import NEW_IMAGE
from tests.helpers import SAMPLE_IMG_DIR
from tests.wx_helpers import HAS_WEBCAM, NoFrameCapture, create_app, run_diag

IMG_LIST = [
    os.path.join(SAMPLE_IMG_DIR, f) for f in ["Entwurf.jpg", "calendar_icon.png"]
]


class TestDialogs(TestCase):
    def test_message_dlg(self):
        with create_app() as f:
            md = CustomMessageDialog("Message", "title", f)
            wx.CallAfter(md.OnClose, None)
            assert md.ShowModal() == wx.ID_CANCEL
            assert not md.okay

            md = CustomMessageDialog("Message", "title", f)
            wx.CallAfter(md.OnOK, None)
            md.ShowModal()
            assert md.okay

            md = CustomMessageDialog("Message", "title", f, cancel_only=True)
            wx.CallAfter(md.OnOK, None)
            assert md.ShowModal() == wx.ID_CANCEL

    def test_dialog_base(self):
        with create_app():
            d = TwoButtonDialogBase()
            d.OnTakePic(None)
            d.OnClose(None)

    def test_change_date_dialog(self):
        with create_app() as f:
            dlg = ChangeDateDialog(f, start=wx.DateTime(3, 2, 2021, 5, 6, 7))
            assert dlg.picked is None
            run_diag(dlg, lambda: dlg.OnOK(None), destroy=False)
            assert dlg.picked.IsEqualTo(wx.DateTime(3, 2, 2021, 5, 6, 7))
            dlg.Destroy()

            # Canceling picks nothing
            dlg = ChangeDateDialog(f)
            run_diag(dlg, lambda: dlg.OnClose(None), destroy=False)
            assert dlg.picked is None
            dlg.Destroy()

            # "Now" picks the current time
            dlg = ChangeDateDialog(f, start=wx.DateTime(3, 2, 2021, 5, 6, 7))
            before = wx.DateTime.Now()
            run_diag(dlg, lambda: dlg.set_now_and_close(None), destroy=False)
            assert dlg.picked.IsLaterThan(before) or dlg.picked.IsEqualTo(before)
            dlg.Destroy()

    def test_photo_exists_dialog(self):
        with create_app():
            # A destroyed dialog cannot be shown again, so create a new one each time.
            photo_dlg = PhotoWithSameDateExistsDialog(IMG_LIST)

            def test_1():
                photo_dlg.OnNext(None)
                photo_dlg.OnPrev(None)
                photo_dlg.OnSelect(None)

            run_diag(photo_dlg, test_1)
            assert photo_dlg.chosenImgInd == 0

            photo_dlg = PhotoWithSameDateExistsDialog(IMG_LIST)
            run_diag(photo_dlg, lambda: photo_dlg.OnClose(None))
            assert photo_dlg.chosenImgInd is None

            photo_dlg = PhotoWithSameDateExistsDialog(IMG_LIST)
            run_diag(photo_dlg, lambda: photo_dlg.OnNew(None))
            assert photo_dlg.chosenImgInd == -1

    def test_no_webcam_error(self):
        with create_app():
            with self.assertRaises(NoWebcamError):
                ShowCapture(None, NoFrameCapture())

    @skipUnless(HAS_WEBCAM, "No webcam available.")
    def test_selfie_dialog(self):
        with create_app():
            photo_dlg = SelfieDialog()

            def take():
                # The dialog to accept the photo is shown by `OnTakePic`
                wx.CallAfter(photo_dlg.accept_diag.OnTakePic, None)
                photo_dlg.OnTakePic(None)

            run_diag(photo_dlg, take)
            assert photo_dlg.taken_img is not None

            photo_dlg = SelfieDialog()

            def take_and_throw():
                wx.CallAfter(photo_dlg.accept_diag.OnClose, None)
                photo_dlg.OnTakePic(None)
                photo_dlg.OnClose(None)

            run_diag(photo_dlg, take_and_throw)
            assert photo_dlg.taken_img is None

    def test_accept_photo(self):
        with create_app():
            img = cv2.imread(os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg"), 0)
            img2 = cv2.merge((img, img, img))
            AcceptPhoto(img=img2)


def answer(dialog_class, fun):
    """Makes a dialog answer by itself instead of showing it.

    `fun` gets the dialog and does what the user would do.
    """

    def show_modal(self):
        fun(self)
        return wx.ID_OK

    return patch.object(dialog_class, "ShowModal", show_modal)


class TestWxDialogs(TestCase):
    """The glue between the controller and the dialogs. The dialogs answer by
    themselves here, as there is no user to click."""

    def setUp(self):
        self.app = wx.App()
        self.addCleanup(self.app.Destroy)
        self.dialogs = WxDialogs()
        old_img_folder = folders.img_folder
        folders.img_folder = SAMPLE_IMG_DIR
        self.addCleanup(setattr, folders, "img_folder", old_img_folder)

    def test_confirm(self):
        seen = []

        def click_ok(dlg):
            seen.append((dlg.GetTitle(), dlg.GetSize()))
            dlg.OnOK(None)

        with answer(CustomMessageDialog, click_ok):
            assert self.dialogs.confirm("Sure?", "Title", "Yes", "No") is True
        assert seen[0][0] == "Title"
        with answer(CustomMessageDialog, lambda d: d.OnClose(None)):
            assert self.dialogs.confirm("Sure?", "Title", "Yes", "No") is False

    def test_info(self):
        shown = []
        with answer(CustomMessageDialog, lambda d: shown.append(d.GetTitle())):
            self.dialogs.info("Text", "Info title")
        assert shown == ["Info title"]

    def test_choose_image(self):
        with answer(PhotoWithSameDateExistsDialog, lambda d: d.OnSelect(None)):
            assert self.dialogs.choose_image(["Entwurf.jpg"]) == 0
        with answer(PhotoWithSameDateExistsDialog, lambda d: d.OnNew(None)):
            assert self.dialogs.choose_image(["Entwurf.jpg"]) == NEW_IMAGE
        with answer(PhotoWithSameDateExistsDialog, lambda d: d.OnClose(None)):
            assert self.dialogs.choose_image(["Entwurf.jpg"]) is None

    def test_pick_date(self):
        start = datetime(2021, 3, 4, 5, 6, 7)
        with answer(ChangeDateDialog, lambda d: d.OnOK(None)):
            assert self.dialogs.pick_date(start) == start
        with answer(ChangeDateDialog, lambda d: d.OnClose(None)):
            assert self.dialogs.pick_date(start) is None
        with answer(ChangeDateDialog, lambda d: d.set_now_and_close(None)):
            picked = self.dialogs.pick_date(start)
        assert abs((datetime.now() - picked).total_seconds()) < 5

    def test_show_photo(self):
        shown = []
        with answer(PhotoShow, lambda d: shown.append(d.f_name)):
            self.dialogs.show_photo(IMG_LIST[0])
        assert shown == [IMG_LIST[0]]

    def test_ask_folder(self):
        with patch.object(dialogs, "ask_for_dir", return_value="/some/folder"):
            assert self.dialogs.ask_folder() == "/some/folder"
        with patch.object(dialogs, "ask_for_dir", return_value=""):
            assert self.dialogs.ask_folder() is None

    @skipUnless(not HAS_WEBCAM, "There is a webcam.")
    def test_selfie_without_webcam(self):
        with self.assertRaises(NoWebcamError):
            self.dialogs.take_selfie("/tmp/not_taken.png")

    def test_selfie_is_saved(self):
        import tempfile

        img = cv2.imread(IMG_LIST[0])

        class FakeSelfieDialog:
            """The dialog with the webcam, where the user takes a picture or not."""

            def __init__(self, taken_img=None):
                self.taken_img = taken_img

            def ShowModal(self):
                return wx.ID_OK

            def Destroy(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "sub", "taken.png")
            with patch.object(dialogs, "SelfieDialog", lambda: FakeSelfieDialog(img)):
                assert self.dialogs.take_selfie(target) is True
            assert os.path.isfile(target)
            assert cv2.imread(target).shape == img.shape

            # Nothing is saved if no picture was taken
            other = os.path.join(folder, "other.png")
            with patch.object(dialogs, "SelfieDialog", lambda: FakeSelfieDialog()):
                assert self.dialogs.take_selfie(other) is False
            assert not os.path.exists(other)
