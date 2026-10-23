import os
import shutil
import tempfile
from datetime import datetime
from unittest import TestCase

from story_time.images import (
    NEW_IMAGE,
    copy_img_file_to_imgs,
    find_all_imgs_with_same_date,
    find_new_name,
    is_supported_image,
)
from tests.helpers import SAMPLE_IMG_DIR

SAMPLE_IMG = os.path.join(SAMPLE_IMG_DIR, "Entwurf.jpg")
IMG_DATE = datetime(2020, 12, 2, 5, 31)
IMG_NAME = "IMG_20201202_053100"


class TestImageNames(TestCase):
    def test_supported_images(self):
        for name in ["a.jpg", "a.JPG", "a.jpeg", "b.png", "c.BMP", "/x/y/z.png"]:
            assert is_supported_image(name), name
        for name in ["a.gif", "a", "a.jpg.txt", "jpg", ".png", ""]:
            assert not is_supported_image(name), name

    def test_img_finding(self):
        r = find_all_imgs_with_same_date(SAMPLE_IMG_DIR, "Entwurf.jpg")
        assert r[0] == "Entwurf.jpg"
        assert find_all_imgs_with_same_date(SAMPLE_IMG_DIR, "NoSuchImage") == []

    def test_new_name(self):
        img_name = "test_img"
        ext = ".jpg"
        img_list = [f"{img_name}_{k}{ext}" for k in range(5)]
        new_name = find_new_name(img_name, img_list[:-1], ext)
        assert new_name + ext == img_list[-1]
        with self.assertRaises(ValueError):
            find_new_name(img_name, img_list, ext, max_n_imgs=3)


class TestImageCopying(TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="story_time_test_imgs_")
        self.addCleanup(shutil.rmtree, self.folder, True)

    def copy(self, choose_image=None):
        return copy_img_file_to_imgs(SAMPLE_IMG, self.folder, IMG_DATE, choose_image)

    def files(self):
        return sorted(os.listdir(self.folder))

    def test_copy_is_named_after_the_date(self):
        path = self.copy()
        assert path == os.path.join(self.folder, IMG_NAME + ".jpg")
        assert self.files() == [IMG_NAME + ".jpg"]

    def test_date_is_taken_from_the_file_name(self):
        named = os.path.join(self.folder, "IMG_20190304_101500.jpg")
        shutil.copy(SAMPLE_IMG, named)
        out = tempfile.mkdtemp(prefix="story_time_test_out_")
        self.addCleanup(shutil.rmtree, out, True)
        path = copy_img_file_to_imgs(named, out)
        assert path == os.path.join(out, "IMG_20190304_101500.jpg")

    def test_chooser_is_not_asked_without_same_date(self):
        asked = []
        self.copy(lambda files: asked.append(files))
        assert asked == []

    def test_same_date_adds_new_image_by_default(self):
        self.copy()
        path = self.copy()
        assert path == os.path.join(self.folder, IMG_NAME + "_0.jpg")
        assert self.files() == [IMG_NAME + ".jpg", IMG_NAME + "_0.jpg"]

    def test_chooser_gets_the_existing_images(self):
        self.copy()
        asked = []

        def choose(files):
            asked.append(files)
            return NEW_IMAGE

        path = self.copy(choose)
        assert asked == [[IMG_NAME + ".jpg"]]
        assert path.endswith(IMG_NAME + "_0.jpg")

    def test_use_existing_image(self):
        first = self.copy()
        path = self.copy(lambda files: 0)
        assert path == first
        assert self.files() == [IMG_NAME + ".jpg"]

    def test_abort(self):
        self.copy()
        assert self.copy(lambda files: None) is None
        assert self.files() == [IMG_NAME + ".jpg"]

    def test_several_images_with_same_date(self):
        for _ in range(3):
            self.copy()
        assert self.files() == [
            IMG_NAME + ".jpg",
            IMG_NAME + "_0.jpg",
            IMG_NAME + "_1.jpg",
        ]
