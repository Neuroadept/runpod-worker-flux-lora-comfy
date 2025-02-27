import os
from pathlib import Path


COMFY_OUTPUT_PATH = Path(os.environ.get("COMFY_OUTPUT_PATH", "/comfyui/output"))

MOUNTED_STORAGE = Path("/runpod-volume")

INPUT_IMG_DIR = Path("/comfyui/input")
INPUT_IMG_PATH = INPUT_IMG_DIR / "input_img.png"

MODELS_DIR = Path("/comfyui/models")
LORA_NAME: str = "lora.safetensors"
UNET_NAME: str = "flux1-dev.safetensors"
LOCAL_LORA_PATH = MODELS_DIR / "loras" / LORA_NAME
