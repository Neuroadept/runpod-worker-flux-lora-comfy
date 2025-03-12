# Define variables
IMAGE_NAME := runpod-worker-flux-lora-comfy
REGISTRY := gfx73/ # Optional, set if pushing to a registry
ENV_FILE := $(shell pwd)/.env # Absolute path to the .env file
TEST_INPUT_FILE := $(strip $(shell pwd))/test_input.json # Absolute path to the test input file
SRC_DIR := $(strip $(shell pwd))/src
GET_TAG := $(shell git rev-parse --short HEAD)
FULL_IMAGE_NAME := $(strip $(REGISTRY))$(IMAGE_NAME)


# Read the release version from the VERSION file
RELEASE_VERSION := $(shell cat VERSION 2>/dev/null || echo "latest")

# Target 1: Build image by commit (no push)
build-commit:
	@echo "Building Docker image with commit-based tag..."
	./cicd/build-commit-image.sh

# Target 2: Build release image (with push)
build-release:
	@echo "Building release Docker image with auto-incremented version..."
	./cicd/release.sh

# Run the commit-based image
run-commit:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		$(FULL_IMAGE_NAME):$(GET_TAG)

# Run the release image
run-release:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		$(FULL_IMAGE_NAME):$(RELEASE_VERSION)

# Run the commit-based image interactively
run-commit-interactive:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		-p 8188:8188 \
		-it $(FULL_IMAGE_NAME):$(GET_TAG) bash

# Run the release image interactively
run-release-interactive:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		-p 8188:8188 \
		-it $(FULL_IMAGE_NAME):$(RELEASE_VERSION) bash

run-dev:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(SRC_DIR)):/src:ro \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		$(FULL_IMAGE_NAME):$(RELEASE_VERSION)

run-dev-interactive:
	docker run --env-file $(ENV_FILE) \
		-v $(strip $(SRC_DIR)):/src:ro \
		-v $(strip $(TEST_INPUT_FILE)):/test_input.json:ro \
		--gpus all \
		-p 8188:8188 \
		-it $(FULL_IMAGE_NAME):$(RELEASE_VERSION) bash