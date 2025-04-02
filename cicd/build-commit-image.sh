#!/bin/bash

# Get the current Git commit hash
COMMIT_HASH=$(git rev-parse --short HEAD)

# Check if the commit hash was retrieved successfully
if [ -z "$COMMIT_HASH" ]; then
    echo "Error: Unable to retrieve Git commit hash."
    exit 1
fi

# Define the Docker image name and tag
IMAGE_NAME="comfy"
TAG="${COMMIT_HASH}"
REGISTRY="neuroproduction"

# Build the Docker image
echo "Building Docker image ${REGISTRY}/${IMAGE_NAME}:${TAG}..."
docker build -t "${REGISTRY}/${IMAGE_NAME}:${TAG}" .

# Exit with success
exit 0