INPUT_SCHEMA = {
    "workflow": {
        "type": dict,
        "required": True,
    },
    "image_s3_path": {
        "type": str,
        "required": True,
    },
    "upload_path": {
        "type": str,
        "required": True,
    },
    "lora_download_path": {
        "type": str,
        "required": True,
    },
    "lora_params": {
        "type": dict,
        "required": True,
    },
    "chat_id": {
        "type": int,
        "required": True,
    }
}
