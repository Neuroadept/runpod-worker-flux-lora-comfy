FROM alpine:3.21.3 AS weights
RUN apk add --update --no-cache aria2 && rm -rf /var/cache/apk/*
RUN mkdir /models/ && \
    aria2c -x16 -s16 -c -d /models/ -o clip_l.safetensors \
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" && \
    aria2c -x16 -s16 -c -d /models/ -o t5xxl_fp16.safetensors \
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors" && \
    aria2c -x16 -s16 -c -d /models/ -o flux_dev_vae.safetensors \
        "https://huggingface.co/vpakarinen/flux-dev-vae-clip/resolve/main/flux_dev_vae.safetensors" && \
    aria2c -x16 -s16 -c -d /models/ -o flux1-dev.safetensors \
        "https://huggingface.co/Corcelio/flux-dev-unet/resolve/main/flux1-dev.sft"


FROM pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime

COPY --from=weights /models/clip_l.safetensors /models/clip/clip_l.safetensors
COPY --from=weights /models/t5xxl_fp16.safetensors /models/clip/t5xxl_fp16.safetensors
COPY --from=weights /models/flux_dev_vae.safetensors /models/vae/ae.safetensors
COPY --from=weights /models/flux1-dev.safetensors /models/unet/flux1-dev.safetensors
# COPY --from=weights /models /models/checkpoints

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1
# Speed up some cmake builds
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
    libgl1 ffmpeg libsm6 libxext6 git && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

RUN pip install comfy-cli==1.3.7 && \
    comfy --skip-prompt --workspace /comfyui install --cuda-version 12.4 --nvidia --version 0.3.14

WORKDIR /
COPY builder/requirements.txt /requirements.txt
RUN pip install -r requirements.txt --no-cache-dir && \
    rm /requirements.txt

ADD src /src

ADD *snapshot*.json /
RUN chmod +x /src/start.sh /src/restore_snapshot.sh
RUN /src/restore_snapshot.sh

ADD extra_model_paths.yaml /comfyui
# RUN touch /models/loras/

CMD ["/src/start.sh"]
