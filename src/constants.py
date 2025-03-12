import os
from pathlib import Path


COMFY_OUTPUT_PATH = Path(os.environ.get("COMFY_OUTPUT_PATH", "/comfyui/output"))

MOUNTED_STORAGE = Path("/runpod-volume")

INPUT_IMG_DIR = Path("/comfyui/input")
INPUT_IMG_PATH = INPUT_IMG_DIR / "input_img.png"

MODELS_DIR = Path("/models")
UNET_NAME: str = "flux1-dev.safetensors"
LORAS_DIR = MODELS_DIR / "loras"


# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 50
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 500
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = int(os.environ.get("COMFY_POLLING_INTERVAL_MS", 250))
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = int(os.environ.get("COMFY_POLLING_MAX_RETRIES", 5000))
# Host where ComfyUI is running
COMFY_HOST = "127.0.0.1:8188"
# Enforce a clean state after each job is done
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"
