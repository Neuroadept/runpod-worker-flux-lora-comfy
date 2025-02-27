import base64
import shutil
from contextlib import contextmanager
from pathlib import Path

from constants import INPUT_IMG_DIR, INPUT_IMG_PATH, MOUNTED_STORAGE
from s3_manager import S3Manager


def prepare_input_image(img_key: str | None, imgs_in_s3: bool, s3_manager: S3Manager) -> None:
    if img_key is None:
        return
    if imgs_in_s3:
        s3_manager.download_file(s3_key=img_key, local_path=INPUT_IMG_PATH)
    else:
        shutil.copy(MOUNTED_STORAGE / img_key, INPUT_IMG_PATH)


@contextmanager
def prepare_input_image_contextmanager(img_key: str | None, img_in_s3: bool, s3_manager: S3Manager) -> None:
    for file_path in INPUT_IMG_DIR.iterdir():
        file_path.unlink(missing_ok=True)
    try:
        prepare_input_image(img_key=img_key, imgs_in_s3=img_in_s3, s3_manager=s3_manager)
        yield
    finally:
        for file_path in INPUT_IMG_DIR.iterdir():
            file_path.unlink(missing_ok=True)


@contextmanager
def temp_folder(folder_path: Path) -> None:
    shutil.rmtree(folder_path, ignore_errors=True)
    folder_path.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        shutil.rmtree(folder_path, ignore_errors=True)


@contextmanager
def temp_images(folder_path: Path):
    for file_path in folder_path.iterdir():
        file_path.unlink(missing_ok=True)
    try:
        yield
    finally:
        for file_path in folder_path.iterdir():
            file_path.unlink(missing_ok=True)


def image_to_base64(image_path: Path) -> str:
    """
    Reads an image file and converts it to a base64 encoded string.

    :param image_path: Path to the image file.
    :return: Base64 encoded string of the image.
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string
