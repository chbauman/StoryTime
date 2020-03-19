import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase

import cv2
import wx

import lib
from lib.util import (
    create_xml_and_img_folder,
    rep_newlines_with_space,
    pad_int_str,
    get_img_name_from_time,
    extract_date_from_image_name,
    get_time_from_file,
    get_file_modified_wx_dt,
    FileDrop,
    update_folder,
    write_folder_to_file,
    get_info_from_file,
    format_date_time,
    ChangeDateDialog,
    PhotoWithSameDateExistsDialog,
    SelfieDialog,
    find_new_name,
    find_all_imgs_with_same_date,
    copy_img_file_to_imgs,
    create_dir,
    TwoButtonDialogBase,
    AcceptPhoto,
    CustomMessageDialog,
    ask_for_dir,
)

DATA_DIR = os.path.join(Path(__file__).parent, "test_data")
SAMPLE_IMG_DIR = os.path.join(DATA_DIR, "sample_imgs")
img_dir = os.path.join(DATA_DIR, "Img")
xml_dir = os.path.join(DATA_DIR, "XML")


@contextmanager
def create_test_dirs():
    """Creates and removes temporary folders for testing."""
    create_dir(img_dir)
    create_dir(xml_dir)
    yield
    shutil.rmtree(img_dir)
    shutil.rmtree(xml_dir)


@contextmanager
def create_app():
    a = wx.App()
    yield
    a.Destroy()


@contextmanager
def change_info_txt(dir_to_set):
    with open("Info.txt", "r") as f:
        curr_info_txt = f.read()
    lib.util.data_path = dir_to_set
    write_folder_to_file()
    yield
    with open("Info.txt", "w") as f:
        f.write(curr_info_txt)


@contextmanager
def replace_dir_ask(new_ask_fun):
    ask_fun = lib.util.ask_for_dir
    lib.util.ask_for_dir = new_ask_fun
    yield
    lib.util.ask_for_dir = ask_fun


class TestFileSystem(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not os.path.isdir(DATA_DIR):
            os.mkdir(DATA_DIR)

    def test_dir_creation(self):
        try:
            create_xml_and_img_folder(DATA_DIR)
            create_xml_and_img_folder(DATA_DIR)
        finally:
            assert os.path.isdir(img_dir)
            os.removedirs(img_dir)
            assert os.path.isdir(xml_dir)
            os.removedirs(xml_dir)
        assert not os.path.isdir(img_dir)

    def test_modified_time(self):
        test_file = os.path.join(DATA_DIR, "test_file")
        t_now = wx.DateTime.Now()
        with open(test_file, "w") as f:
            f.write("test")
        t_after = wx.DateTime.Now()
        t_meas_1 = get_file_modified_wx_dt(test_file)
        t_meas = get_time_from_file(test_file)
        try:
            assert t_meas.IsEqualTo(t_meas_1)
            assert t_meas.IsEqualTo(t_now) or t_meas.IsEqualTo(t_after)
        finally:
            os.remove(test_file)

    def test_info_file(self):
        with change_info_txt(DATA_DIR):
            with open("Info.txt", "r") as f:
                assert f.read().strip() == DATA_DIR

            f_path = get_info_from_file(False)
            assert f_path == DATA_DIR

            os.remove("Info.txt")

            def new_ask(_=None):
                return DATA_DIR

            with replace_dir_ask(new_ask):
                get_info_from_file(True)

        if os.path.isdir(img_dir):
            os.removedirs(img_dir)
        if os.path.isdir(xml_dir):
            os.removedirs(xml_dir)

    def test_img_finding(self):
        f_img = "Entwurf.jpg"
        r = find_all_imgs_with_same_date(SAMPLE_IMG_DIR, f_img)
        assert r[0] == f_img

    def test_img_copying(self):
        update_folder(DATA_DIR)
        create_dir(lib.util.img_folder)
        create_dir(lib.util.xml_folder)
        img_path = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")
        copy_img_file_to_imgs(img_path)
        a = wx.App()

        def fun(dlg):
            dlg.OnNew(None)

        copy_img_file_to_imgs(img_path, None, fun)

        def fun2(dlg):
            dlg.OnNext(None)
            dlg.OnClose(None)

        copy_img_file_to_imgs(img_path, None, fun2)

        def fun3(dlg):
            dlg.OnSelect(None)

        copy_img_file_to_imgs(img_path, None, fun3)

        shutil.rmtree(lib.util.img_folder)
        os.removedirs(lib.util.xml_folder)
        a.Destroy()

    pass


class TestUtil(TestCase):
    def test_newline_replace(self):
        inp = "sdl sdk \n e sie \n"
        exp_out = "sdl sdk  e sie "
        out = rep_newlines_with_space(inp)
        self.assertEqual(exp_out, out)

    def test_string_pad(self):
        inp = 4
        exp_out = "0004"
        out = pad_int_str(inp, 4)
        self.assertEqual(exp_out, out)

    def test_name_from_time(self):
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        exp_name = "IMG_20201202_053100"
        name = get_img_name_from_time(wx_dt)
        self.assertEqual(name, exp_name)

    def test_date_extraction(self):
        f_path = "test/IMG_20201202_053100.jpg"
        wx_dt = extract_date_from_image_name(f_path)
        assert wx_dt.IsEqualTo(wx.DateTime(2, 11, 2020, 5, 31))

    def test_invalid_date_extraction(self):
        f_path = "test/IMG_00001202_053100.jpg"
        wx_dt = extract_date_from_image_name(f_path)
        assert wx_dt is None
        f_path = "test/IMG_20003202_053100.jpg"
        wx_dt = extract_date_from_image_name(f_path)
        assert wx_dt is None

    def test_update_folder(self):
        update_folder(DATA_DIR)
        assert lib.util.data_path == DATA_DIR

    def test_format_dt(self):
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        exp_str = " 2.12.2020, Time: 05:31:00"
        res = format_date_time(wx_dt)
        assert ",".join(res.split(",")[1:]) == exp_str

    def test_new_name(self):
        img_name = "test_img"
        ext = ".jpg"
        img_list = [f"{img_name}_{k}{ext}" for k in range(5)]
        new_name = find_new_name(img_name, img_list[:-1], ext)
        assert new_name + ext == img_list[-1]
        with self.assertRaises(ValueError):
            find_new_name(img_name, img_list, ext, max_n_imgs=3)

    pass


def init_app():
    return wx.App(), wx.Frame()


def run_diag(dlg, fun, destroy: bool = True):
    wx.CallAfter(fun)
    dlg.ShowModal()
    if destroy:
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

        with create_app():
            app, frame = init_app()
            md = CustomMessageDialog("Message", "title", frame)
            wx.CallAfter(abort, md)
            assert md.ShowModal() == wx.ID_CANCEL

            print(f"Cancel: {wx.ID_CANCEL}")
            print(f"Ok: {wx.ID_OK}")
            print(f"Cancel: {wx.ID_YES}")

            md = CustomMessageDialog("Message", "title", frame)
            wx.CallAfter(ok, md)
            assert md.ShowModal() == wx.ID_CANCEL

            md = CustomMessageDialog("Message", "title", frame, cancel_only=True)
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
        app, frame = init_app()
        dlg = ChangeDateDialog(frame)

        def clickOK():
            dlg.OnOK(None)

        run_diag(dlg, clickOK)

        def cancel():
            dlg.OnClose(None)

        run_diag(dlg, cancel)

    def test_photo_exists_dialog(self):
        app, frame = init_app()
        img_list = [
            os.path.join(SAMPLE_IMG_DIR, f)
            for f in ["Entwurf.jpg", "calendar_icon.png"]
        ]
        photo_dlg = PhotoWithSameDateExistsDialog(img_list, frame)

        def test_1():
            photo_dlg.OnNext(None)
            photo_dlg.OnPrev(None)
            photo_dlg.OnSelect(None)

        run_diag(photo_dlg, test_1)
        assert photo_dlg.chosenImgInd == 0

        def test_2():
            photo_dlg.OnClose(None)

        run_diag(photo_dlg, test_2)

        def test_3():
            photo_dlg.OnNew(None)

        run_diag(photo_dlg, test_3)
        assert photo_dlg.chosenImgInd == -1

    def test_selfie_dialog(self):
        app, frame = init_app()
        photo_dlg = SelfieDialog(frame)

        def test_1():
            def inner():
                photo_dlg.accept_diag.OnTakePic(None)

            photo_dlg.OnTakePic(None, inner)

        run_diag(photo_dlg, test_1)
        assert photo_dlg.taken_img is not None

        photo_dlg = SelfieDialog(frame)

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
