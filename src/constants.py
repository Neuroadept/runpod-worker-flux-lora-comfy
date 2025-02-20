import os
from pathlib import Path


COMFY_OUTPUT_PATH = Path(os.environ.get("COMFY_OUTPUT_PATH", "/comfyui/output"))

MOUNTED_STORAGE = Path("/runpod-volume")

INPUT_IMGS_DIR = Path("/input_imgs")

MODELS_DIR = Path("/comfyui/models")
LORA_NAME: str = "loras/lora.safetensors"
UNET_NAME: str = "unet/flux1-dev.safetensors"
LOCAL_LORA_PATH = MODELS_DIR / LORA_NAME
