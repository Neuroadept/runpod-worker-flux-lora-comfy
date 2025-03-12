INPUT_SCHEMA = {
    "workflow": {
        "type": dict,
        "required": True,
    },
    "image_s3_path": {
        "type": str,
        "required": False,
        "default": "",
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
    },
    "lora_name": {
        "type": str,
        "required": True,
    }
}
