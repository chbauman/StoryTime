import os
from pathlib import Path
from unittest import TestCase

from lib.util import create_xml_and_img_folder, rep_newlines_with_space, pad_int_str

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
            # create_xml_and_img_folder(DATA_DIR)
        finally:
            assert os.path.isdir(img_dir)
            os.removedirs(img_dir)
            assert os.path.isdir(xml_dir)
            os.removedirs(xml_dir)

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

    pass
