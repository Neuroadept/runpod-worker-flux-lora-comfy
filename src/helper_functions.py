import base64
import shutil
from contextlib import contextmanager
from pathlib import Path

from constants import INPUT_IMGS_DIR, MOUNTED_STORAGE
from s3_manager import S3Manager


def prepare_input_images(imgs_path: str | None, imgs_in_s3: bool, s3_manager: S3Manager) -> None:
    if imgs_path is None:
        return
    if imgs_in_s3:
        s3_manager.download_directory(s3_prefix=imgs_path, local_directory=INPUT_IMGS_DIR)
    else:
        shutil.copytree(MOUNTED_STORAGE / imgs_path, INPUT_IMGS_DIR)


@contextmanager
def prepare_input_images_contextmanager(imgs_path: str | None, imgs_in_s3: bool, s3_manager: S3Manager) -> None:
    try:
        prepare_input_images(imgs_path=imgs_path, imgs_in_s3=imgs_in_s3, s3_manager=s3_manager)
        yield
    finally:
        shutil.rmtree(INPUT_IMGS_DIR, ignore_errors=True)


@contextmanager
def temp_folder(folder_path: Path) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        shutil.rmtree(folder_path, ignore_errors=True)


def image_to_base64(image_path: Path) -> str:
    """
    Reads an image file and converts it to a base64 encoded string.

    :param image_path: Path to the image file.
    :return: Base64 encoded string of the image.
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string