import os
from pathlib import Path
from unittest import TestCase

import wx

import lib
from lib.util import create_xml_and_img_folder, rep_newlines_with_space, pad_int_str, get_img_name_from_time, \
    extract_date_from_image_name, get_time_from_file, get_file_modified_wx_dt, FileDrop, update_folder, \
    write_folder_to_file, get_info_from_file, format_date_time, ChangeDateDialog

DATA_DIR = os.path.join(Path(__file__).parent, "test_data")


class TestFileSystem(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not os.path.isdir(DATA_DIR):
            os.mkdir(DATA_DIR)

    def test_dir_creation(self):
        img_dir = os.path.join(DATA_DIR, "Img")
        xml_dir = os.path.join(DATA_DIR, "XML")
        try:
            create_xml_and_img_folder(DATA_DIR)
            create_xml_and_img_folder(DATA_DIR)
        finally:
            assert os.path.isdir(img_dir)
            os.removedirs(img_dir)
            assert os.path.isdir(xml_dir)
            os.removedirs(xml_dir)

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
        with open("Info.txt", "r") as f:
            curr_info_txt = f.read()

        try:
            lib.util.data_path = DATA_DIR
            write_folder_to_file()
            with open("Info.txt", "r") as f:
                assert f.read().strip() == DATA_DIR

            f_path = get_info_from_file(False)
            assert f_path == DATA_DIR
        finally:
            with open("Info.txt", "w") as f:
                f.write(curr_info_txt)

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

    def test_update_folder(self):
        update_folder(DATA_DIR)
        assert lib.util.data_path == DATA_DIR

    def test_format_dt(self):
        wx_dt = wx.DateTime(2, 11, 2020, 5, 31)
        exp_str = " 2.12.2020, Time: 05:31:00"
        res = format_date_time(wx_dt)
        assert ",".join(res.split(",")[1:]) == exp_str

    pass


def init_app():
    return wx.App(), wx.Frame()


def run_diag(dlg, fun):
    wx.CallAfter(fun)
    dlg.ShowModal()
    dlg.Destroy()


class TestGUIElements(TestCase):

    def test_file_drop(self):
        class DummyFrame:
            def set_img_with_date(self, *args, **kwargs):
                pass

        d_frame = DummyFrame()
        fd = FileDrop(None, d_frame)
        fd.OnDropFiles(0, 0, ["test/IMG_20201202_053100.jpg"])

    def test_change_date_dialog(self):
        app, frame = init_app()
        dlg = ChangeDateDialog(frame)

        def clickOK():
            dlg.OnOK(None)

        run_diag(dlg, clickOK)

        def cancel():
            dlg.OnClose(None)

        run_diag(dlg, cancel)