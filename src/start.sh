#!/usr/bin/env bash

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"


# Check if VIBEAI_NOT_ONLY_GPU is set to true
if [ "$VIBEAI_NOT_ONLY_GPU" == "true" ]; then
    echo "runpod-worker-comfy: Starting ComfyUI (without --gpu-only)"
    python3 /comfyui/main.py --disable-auto-launch --disable-metadata &
else
    echo "runpod-worker-comfy: Starting ComfyUI"
    python3 /comfyui/main.py --disable-auto-launch --disable-metadata --gpu-only &
fi

echo "runpod-worker-comfy: Starting RunPod Handler"
python3 -u /src/rp_handler.py
