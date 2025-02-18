import os
from pathlib import Path


COMFY_OUTPUT_PATH = Path(os.environ.get("COMFY_OUTPUT_PATH", "/comfyui/output"))

MOUNTED_STORAGE = Path("/runpod-volume")

INPUT_IMGS_DIR = Path("/input_imgs")
