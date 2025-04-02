#!/bin/bash

# File to store the current version
VERSION_FILE="VERSION"

# Read the current version from the file
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE")
else
    CURRENT_VERSION="0.0.0"
fi

# Increment the patch version (major.minor.patch)
IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
patch=$((patch + 1))
NEW_VERSION="${major}.${minor}.${patch}"

# Update the version file
echo "$NEW_VERSION" > "$VERSION_FILE"

# Define the Docker image name and tag
IMAGE_NAME="comfy"
REGISTRY="neuroproduction"
TAG="$NEW_VERSION"

# Build the Docker image
echo "Building release Docker image ${IMAGE_NAME}:${TAG}..."
docker build -t "${REGISTRY}/${IMAGE_NAME}:${TAG}" .

if [ ! -z "$REGISTRY" ]; then
    docker push "${REGISTRY}/${IMAGE_NAME}:${TAG}"
    echo "Pushed image to registry: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
fi

# Exit with success
exit 0