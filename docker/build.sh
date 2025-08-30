#!/bin/bash
# Build script for ES Inventory Hub Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build context
BUILD_CONTEXT="."
IMAGE_PREFIX="es-inventory-hub"

print_status "Building ES Inventory Hub Docker images..."

# Build collectors image
print_status "Building collectors image..."
docker build \
    -f docker/Dockerfile.collectors \
    -t ${IMAGE_PREFIX}-collectors:latest \
    ${BUILD_CONTEXT}

if [ $? -eq 0 ]; then
    print_status "Collectors image built successfully"
else
    print_error "Failed to build collectors image"
    exit 1
fi

# Build dashboard image
print_status "Building dashboard image..."
docker build \
    -f docker/Dockerfile.dashboard \
    -t ${IMAGE_PREFIX}-dashboard:latest \
    ${BUILD_CONTEXT}

if [ $? -eq 0 ]; then
    print_status "Dashboard image built successfully"
else
    print_error "Failed to build dashboard image"
    exit 1
fi

# List built images
print_status "Built images:"
docker images | grep ${IMAGE_PREFIX}

print_status "Build completed successfully!"
print_status "You can now run the services with: docker-compose up -d"
