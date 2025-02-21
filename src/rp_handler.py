import runpod
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO

from constants import INPUT_IMGS_DIR, COMFY_OUTPUT_PATH, LOCAL_LORA_PATH, LORA_NAME, UNET_NAME
from helper_functions import prepare_input_images_contextmanager, image_to_base64, temp_folder
from kafka_producer_manager import check_kafka_creds, kafka_manager, push_inference_completed_msg
from s3_manager import S3Manager

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
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Validate 'images' in input, if provided
    images_s3_paths = job_input.get("images_s3_path")
    if (
            images_s3_paths is not None and
            (not isinstance(images_s3_paths, list) or any(not isinstance(image, str) for image in images_s3_paths))
    ):
        return (
            None,
            "'images' must be a list of objects with 'name' and 'image' keys",
        )

    upload_path = job_input.get("upload_path")
    if not isinstance(upload_path, str):
        return None, "Upload s3 path is not provided"

    lora_download_path = job_input.get("lora_download_path")
    if not isinstance(lora_download_path, str):
        return None, "Lora download path is not provided"

    lora_params = job_input.get("lora_params")
    if not isinstance(lora_params, dict):
        return None, "Lora params is not provided"

    prompt = lora_params.get("prompt")
    if not isinstance(prompt, str):
        return None, "Prompt is not provided"

    chat_id = job_input.get("chat_id")
    if not isinstance(upload_path, int):
        return None, "chat_id is not provided or not int"

    # Return validated data and no error
    return {
        "workflow": workflow,
        "lora_download_path": lora_download_path,
        "images_s3_paths": images_s3_paths,
        "upload_path": upload_path,
        "lora_params": lora_params,
        "chat_id": chat_id,
    }, None


def check_server(url, retries=500, delay=50):
    """
    Check if a server is reachable via HTTP GET request

    Args:
    - url (str): The URL to check
    - retries (int, optional): The number of times to attempt connecting to the server. Default is 50
    - delay (int, optional): The time in milliseconds to wait between retries. Default is 500

    Returns:
    bool: True if the server is reachable within the given number of retries, otherwise False
    """

    for i in range(retries):
        try:
            response = requests.get(url)

            # If the response status code is 200, the server is up and running
            if response.status_code == 200:
                print(f"runpod-worker-comfy - API is reachable")
                return True
        except requests.RequestException as e:
            # If an exception occurs, the server may not be ready
            pass

        # Wait for the specified delay before retrying
        time.sleep(delay / 1000)

    print(
        f"runpod-worker-comfy - Failed to connect to server at {url} after {retries} attempts."
    )
    return False


def upload_images(images):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.
        server_address (str): The address of the ComfyUI server.

    Returns:
        dict: A list of responses from the server for each image upload.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"runpod-worker-comfy - image(s) upload")

    for image in images:
        name = image["name"]
        image_data = image["image"]
        blob = base64.b64decode(image_data)

        # Prepare the form data
        files = {
            "image": (name, BytesIO(blob), "image/png"),
            "overwrite": (None, "true"),
        }

        # POST request to upload the image
        response = requests.post(f"http://{COMFY_HOST}/upload/image", files=files)
        if response.status_code != 200:
            upload_errors.append(f"Error uploading {name}: {response.text}")
        else:
            responses.append(f"Successfully uploaded {name}")

    if upload_errors:
        print(f"runpod-worker-comfy - image(s) upload with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
        }

    print(f"runpod-worker-comfy - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
    }


def queue_workflow(workflow):
    """
    Queue a workflow to be processed by ComfyUI

    Args:
        workflow (dict): A dictionary containing the workflow to be processed

    Returns:
        dict: The JSON response from ComfyUI after processing the workflow
    """

    # The top level element "prompt" is required by ComfyUI
    data = json.dumps({"prompt": workflow}).encode("utf-8")

    req = urllib.request.Request(f"http://{COMFY_HOST}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id):
    """
    Retrieve the history of a given prompt using its ID

    Args:
        prompt_id (str): The ID of the prompt whose history is to be retrieved

    Returns:
        dict: The history of the prompt, containing all the processing steps and results
    """
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


def base64_encode(img_path):
    """
    Returns base64 encoded image.

    Args:
        img_path (str): The path to the image

    Returns:
        str: The base64 encoded image
    """
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"{encoded_string}"


def process_output_images(upload_path: str):
    # The path where ComfyUI stores the generated images
    image_paths = list(COMFY_OUTPUT_PATH.iterdir())

    print(f"uploading - {image_paths}")

    # The image is in the output folder
    if image_paths:
        s3_manager = S3Manager()
        s3_manager.upload_directory(COMFY_OUTPUT_PATH, upload_path)
        return {
            "status": "success",
            "message": {"upload_path": upload_path},
        }
    else:
        print("runpod-worker-comfy - the image does not exist in the output folder")
        return {
            "status": "error",
            "message": f"the image does not exist in the specified output folder: {COMFY_OUTPUT_PATH}",
        }


def modify_workflow(wf: dict, prompt: str | None):
    if prompt is not None:
        wf["6"]["inputs"]["text"] = prompt
    return wf


def handler(job):
    """
    The main function that handles a job of generating an image.

    This function validates the input, sends a prompt to ComfyUI for processing,
    polls ComfyUI for result, and retrieves generated images.

    Args:
        job (dict): A dictionary containing job details and input parameters.

    Returns:
        dict: A dictionary containing either an error message or a success status with generated images.
    """
    job_input = job["input"]

    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    try:
        check_kafka_creds()
    except ValueError as e:
        return {"error": str(e)}

    # Extract validated data
    chat_id = validated_data["chat_id"]
    workflow = validated_data["workflow"]
    prompt: str = validated_data["lora_params"]["prompt"]
    images_s3_paths: str | None = validated_data.get("images_s3_paths")
    upload_path = validated_data["upload_path"]
    lora_download_path = validated_data["lora_download_path"]

    workflow = modify_workflow(workflow, prompt)

    # Make sure that the ComfyUI API is available
    check_server(
        f"http://{COMFY_HOST}",
        COMFY_API_AVAILABLE_MAX_RETRIES,
        COMFY_API_AVAILABLE_INTERVAL_MS,
    )

    # Upload images if they exist
    s3_manager = S3Manager()

    if images_s3_paths is not None:
        images = []
        with prepare_input_images_contextmanager(imgs_path=images_s3_paths, imgs_in_s3=True, s3_manager=s3_manager):
            for file_path in INPUT_IMGS_DIR.iterdir():
                images.append(image_to_base64(file_path))

        upload_result = upload_images(images)

        if upload_result["status"] == "error":
            upload_result["refresh_worker"] = REFRESH_WORKER
            return upload_result

    # Queue the workflow
    with temp_folder(LOCAL_LORA_PATH.parent), temp_folder(COMFY_OUTPUT_PATH):
        try:
            s3_manager.download_file(s3_key=lora_download_path, local_path=LOCAL_LORA_PATH)
            queued_workflow = queue_workflow(workflow)
            prompt_id = queued_workflow["prompt_id"]
            print(f"runpod-worker-comfy - queued workflow with ID {prompt_id}")
        except Exception as e:
            return {"error": f"Error queuing workflow: {str(e)}", "refresh_worker": True}

        # Poll for completion
        print(f"runpod-worker-comfy - wait until image generation is complete")
        retries = 0
        try:
            while retries < COMFY_POLLING_MAX_RETRIES:
                history = get_history(prompt_id)

                # Exit the loop if we have found the history
                if prompt_id in history and history[prompt_id].get("outputs"):
                    break
                else:
                    # Wait before trying again
                    time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)
                    retries += 1
            else:
                return {"error": "Max retries reached while waiting for image generation", "refresh_worker": True}
        except Exception as e:
            return {"error": f"Error waiting for image generation: {str(e)}", "refresh_worker": True}

        # Get the generated image and return it as URL in an AWS bucket or as base64
        process_output_images(upload_path=upload_path)

        with kafka_manager() as (kafka_producer, topic_name):
            push_inference_completed_msg(
                chat_id=chat_id,
                job_id=job["id"],
                upload_path=upload_path,
                kafka_producer=kafka_producer,
                topic_name=topic_name,
            )

        result = {
            "chat_id": chat_id,
            "rp_job_id": job["id"],
            "upload_path": upload_path,
            "refresh_worker": REFRESH_WORKER,
        }
        return result


# Start the handler only if this script is run directly
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
