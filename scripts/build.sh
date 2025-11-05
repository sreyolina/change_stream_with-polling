#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting the build process..."

# Install dependencies
npm install

# Build the application
npm run build

echo "Build process completed successfully."