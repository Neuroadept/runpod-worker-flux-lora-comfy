import time
import traceback
from functools import wraps

import runpod
from runpod.serverless.utils.rp_validator import validate

from constants import COMFY_OUTPUT_PATH, LOCAL_LORA_PATH
from helper_functions import get_dependencies, prepare_input_image_contextmanager, temp_folder, temp_images
from kafka_producer_manager import KafkaManager
from rp_schema import INPUT_SCHEMA
from s3_manager import S3Manager
from comfy_api import check_server, queue_workflow, get_history
from constants import COMFY_API_AVAILABLE_INTERVAL_MS, COMFY_API_AVAILABLE_MAX_RETRIES, COMFY_POLLING_INTERVAL_MS, \
    COMFY_POLLING_MAX_RETRIES, COMFY_HOST, REFRESH_WORKER
from helper_functions import process_output_images, modify_workflow


def refresh_always(func):
    @wraps(func)
    def refresh_always_wrapper(*args, **kwargs):
        return_data = func(*args, **kwargs)
        return_data["refresh_worker"] = True
        return return_data

    return  refresh_always_wrapper


def fail_on_exception(func):
    @wraps(func)
    def fail_on_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = runpod.RunPodLogger()
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"An error occurred: {str(e)}")
            logger.info(f"Trace: {traceback.format_exc()}")
            return {"error": "error" + str(e), "refresh_worker": True}

    return fail_on_exception_wrapper


def send_to_kafka_on_exception(kafka_manager: KafkaManager, job: dict):
    def send_to_kafka_on_exception_decorator(func):
        @wraps(func)
        def send_to_kafka_on_exception_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                kafka_manager.push_error_msg(
                    job_id=job["id"],
                    error_type=str(type(e)),
                    error_msg=str(e),
                    job_input=job,
                )
                raise e

        return send_to_kafka_on_exception_wrapper

    return send_to_kafka_on_exception_decorator


@refresh_always
@fail_on_exception
def handler(job):
    with KafkaManager.get_and_close() as kafka_manager:
        return send_to_kafka_on_exception(kafka_manager=kafka_manager, job=job)(handler_main)(
            job=job,
            kafka_manager=kafka_manager,
        )


def handler_main(job, kafka_manager: KafkaManager):
    logger = runpod.RunPodLogger()
    deps = ", ".join([f"{dep['path']}=={dep['version']}" for dep in get_dependencies()])
    logger.info(f"Currently using dependencies: {deps}")

    job_input = job["input"]
    if "errors" in (job_input := validate(job_input, INPUT_SCHEMA)):
        logger.error(str(job_input["errors"]))
        kafka_manager.push_error_msg(
            job_id=job["id"],
            error_type="InputValidationError",
            error_msg=str(job_input["errors"]),
            job_input=job_input,
        )
        return {"error": str(job_input["errors"])}
    job_input = job_input["validated_input"]
    logger.info(job_input)

    # Extract validated data
    chat_id = job_input["chat_id"]
    workflow = job_input["workflow"]
    prompt: str = job_input["lora_params"]["prompt"]
    image_s3_path: str | None = job_input["image_s3_path"] or None
    upload_path = job_input["upload_path"]
    lora_download_path = job_input["lora_download_path"]

    workflow = modify_workflow(workflow, prompt, image_s3_path is not None)

    # Make sure that the ComfyUI API is available
    check_server(
        f"http://{COMFY_HOST}",
        COMFY_API_AVAILABLE_MAX_RETRIES,
        COMFY_API_AVAILABLE_INTERVAL_MS,
    )

    # Upload images if they exist
    s3_manager = S3Manager()

    # Queue the workflow
    with (
        prepare_input_image_contextmanager(img_key=image_s3_path, img_in_s3=True, s3_manager=s3_manager),
        temp_folder(LOCAL_LORA_PATH.parent),
        temp_images(COMFY_OUTPUT_PATH)
    ):
        try:
            s3_manager.download_file(s3_key=lora_download_path, local_path=LOCAL_LORA_PATH)
            queued_workflow = queue_workflow(workflow)
            prompt_id = queued_workflow["prompt_id"]
            print(f"runpod-worker-comfy - queued workflow with ID {prompt_id}")
        except Exception as e:
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"An error occurred: {str(e)}")
            logger.info(f"Trace: {traceback.format_exc()}")
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
        img_upload_status = process_output_images(upload_path=upload_path)
        if img_upload_status["status"] == "error":
            return {"error": img_upload_status["message"]}


        kafka_manager.push_inference_completed_msg(
            chat_id=chat_id,
            job_id=job["id"],
            upload_path=upload_path,
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
