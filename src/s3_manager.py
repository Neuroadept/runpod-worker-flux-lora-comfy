import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple
import boto3
from runpod import RunPodLogger

class S3Manager:
    def __init__(self, bucket_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        """
        Initializes the S3Manager with the specified bucket name and endpoint URL.
        :param bucket_name: Name of the S3 bucket (optional, can be set via environment variable).
        :param endpoint_url: Endpoint URL for S3-compatible services (optional, can be set via environment variable).
        """
        self.logger = RunPodLogger()
        self.bucket_name = bucket_name or os.getenv("BUCKET_NAME")
        self.endpoint_url = endpoint_url or os.getenv("ENDPOINT_URL")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION")
        if not self.bucket_name or not self.access_key or not self.secret_key or not self.region:
            raise ValueError("Not all S3 environment variables are set.")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )

    def download_file(self, s3_key: str, local_path: Path) -> None:
        """
        Downloads a single file from S3 to the specified local path.
        :param s3_key: Key of the file in S3.
        :param local_path: Local path where the file will be saved.
        """
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Started downloading {s3_key} to {local_path}")
            self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
            self.logger.info(f"Downloaded {s3_key} to {local_path}")
        except Exception as e:
            self.logger.error(f"Error downloading {s3_key}: {e}")
            raise e

    def download_directory(self, s3_prefix: str, local_directory: Path) -> None:
        """
        Downloads all files from an S3 "directory" to a local directory using multithreading.
        :param s3_prefix: Prefix representing the "directory" in S3.
        :param local_directory: Local directory where files will be downloaded (Path object).
        """
        # Ensure the local directory exists
        local_directory.mkdir(parents=True, exist_ok=True)
        # List all objects with the given prefix
        paginator = self.s3_client.get_paginator('list_objects_v2')
        objects: List[dict] = []
        for result in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
            if 'Contents' not in result:
                self.logger.info(f"No files found in S3 directory: {s3_prefix}")
                return
            objects.extend(result['Contents'])
        # Prepare the arguments for download_file
        s3_keys = (obj['Key'] for obj in objects)
        local_paths = (local_directory / Path(obj['Key']).relative_to(s3_prefix) for obj in objects)
        # Download files using multi-threading
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(self.download_file, s3_keys, local_paths)

    def upload_file(self, local_path: Path, s3_key: str) -> None:
        """
        Uploads a single file from the local filesystem to S3.
        :param local_path: Local path of the file to upload.
        :param s3_key: Key of the file in S3.
        """
        try:
            if not local_path.exists():
                raise FileNotFoundError(f"Local file does not exist: {local_path}")
            self.s3_client.upload_file(str(local_path), self.bucket_name, s3_key)
            self.logger.info(f"Uploaded {local_path} to {s3_key}")
        except Exception as e:
            self.logger.error(f"Error uploading {local_path} to {s3_key}: {e}")
            raise e

    def upload_directory(self, local_directory: Path, s3_prefix: str) -> None:
        """
        Uploads an entire directory from the local filesystem to S3 using multithreading.
        :param local_directory: Local directory to upload.
        :param s3_prefix: Prefix representing the "directory" in S3.
        """
        # Ensure the local directory exists
        if not local_directory.exists() or not local_directory.is_dir():
            raise FileNotFoundError(f"Local directory does not exist or is not a directory: {local_directory}")

        # Walk through the local directory and collect file paths and S3 keys
        file_paths: List[Tuple[Path, str]] = []
        for root, _, files in os.walk(local_directory):
            for file in files:
                local_path = Path(root) / file
                relative_path = local_path.relative_to(local_directory)
                s3_key = str(Path(s3_prefix) / relative_path)
                file_paths.append((local_path, s3_key))

        # Define the upload function using the existing upload_file method
        def upload_file_wrapper(args: Tuple[Path, str]) -> None:
            local_path, s3_key = args
            self.upload_file(local_path, s3_key)

        # Upload files using multi-threading
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(upload_file_wrapper, file_paths)
