"""Handling of the image files of the entries, without any GUI.

The images are copied into the image folder and named after their date.
"""

import os
from datetime import datetime
from shutil import copy2
from typing import Callable, Optional

from story_time.dates import date_of_image_file, img_name_from_time

#: The extensions of the image files that can be added to an entry.
SUPPORTED_EXTENSIONS = ("jpg", "jpeg", "png", "bmp")

#: Choice of the user if an image with the same date exists, other than the index
#: of an existing image to use it for the entry instead of the new one.
NEW_IMAGE = -1


def is_supported_image(path: str) -> bool:
    """Whether the file has the extension of a supported image type."""
    return os.path.splitext(path)[1][1:].lower() in SUPPORTED_EXTENSIONS


def find_all_imgs_with_same_date(imgs_folder: str, img_name: str) -> list[str]:
    """Finds all files starting with string "img_name"
    in folder "img_folder".
    """
    return [f for f in os.listdir(imgs_folder) if f.startswith(img_name)]


def find_new_name(
    img_name: str, same_date_file_list: list[str], ext: str, max_n_imgs: int = 10000
) -> str:
    """Chooses a new filename that is not in the list and
    contains the img_name in the beginning by appending an
    int to the filename separated by an underscore.
    """
    for k in range(max_n_imgs):
        new_name = img_name + "_" + str(k) + ext
        if new_name not in same_date_file_list:
            return img_name + "_" + str(k)

    # If there are already more than `max_n_imgs` images, gives up.
    raise ValueError(f"There are more than {max_n_imgs} images with the same date.")


def copy_img_file_to_imgs(
    img_file: str,
    img_folder: str,
    img_date: Optional[datetime] = None,
    choose_image: Optional[Callable[[list[str]], Optional[int]]] = None,
) -> Optional[str]:
    """Copies an image to the image folder.

    The image is named after its date. If there are already images with the same
    date and time, `choose_image` is asked whether to use one of them for the entry
    instead of adding the new image.

    Args:
        img_file: The image to copy.
        img_folder: The folder to copy it to.
        img_date: The date of the image, taken from the file if not given.
        choose_image: Called with the names of the existing images with the same
            date. Returns the index of the one to use, `NEW_IMAGE` to add the image
            anyway and `None` to abort. By default the image is added.

    Returns:
        The path of the copied or chosen image, `None` if aborted.
    """
    img_date = date_of_image_file(img_file) if img_date is None else img_date
    img_name = img_name_from_time(img_date)
    same_date_files = find_all_imgs_with_same_date(img_folder, img_name)
    _, extension = os.path.splitext(img_file)

    if same_date_files:
        index = NEW_IMAGE if choose_image is None else choose_image(same_date_files)
        if index is None:
            return None
        if index != NEW_IMAGE:
            return os.path.join(img_folder, same_date_files[index])
        img_name = find_new_name(img_name, same_date_files, extension)

    copied_file = os.path.join(img_folder, img_name + extension)
    copy2(img_file, copied_file)
    return copied_file
