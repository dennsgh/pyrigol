#!/bin/bash

# Set variables
IMAGE_NAME="pyrigol"
TAG="latest"

# Navigate to the directory containing the Dockerfile
cd "$(dirname "$0")/.."

# Build the Docker image
docker build -t ${IMAGE_NAME}:${TAG} .

# Verify the image was created correctly
docker images | grep ${IMAGE_NAME}

echo "Docker image ${IMAGE_NAME}:${TAG} has been built."
