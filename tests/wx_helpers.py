"""Helpers for the tests that use wx."""

from contextlib import contextmanager

import cv2
import wx


def _webcam_available() -> bool:
    cap = cv2.VideoCapture(0)
    try:
        return cap.isOpened() and cap.read()[0]
    finally:
        cap.release()


HAS_WEBCAM = _webcam_available()


class NoFrameCapture:
    """Mimics a webcam that does not deliver any frames."""

    @staticmethod
    def read():
        return False, None


@contextmanager
def create_app():
    """An app with a frame, for the tests of single widgets and dialogs."""
    app = wx.App()
    frame = wx.Frame()
    frame.Create(None)
    try:
        yield frame
    finally:
        frame.Destroy()
        app.Yield()  # Only then is the window gone, see test_ui.main_window
        app.Destroy()


def run_diag(dlg, fun, destroy: bool = True):
    """Shows the modal dialog and calls `fun` while it is shown."""
    wx.CallAfter(fun)
    dlg.ShowModal()
    if destroy and dlg:  # The dialog may have destroyed itself when closing.
        dlg.Destroy()
