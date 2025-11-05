#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define variables
APP_NAME="my-app"
DEPLOY_DIR="/var/www/$APP_NAME"
GIT_REPO="https://github.com/username/repo.git"

# Pull the latest code from the repository
echo "Pulling the latest code from the repository..."
git clone $GIT_REPO $DEPLOY_DIR || (cd $DEPLOY_DIR && git pull)

# Navigate to the deployment directory
cd $DEPLOY_DIR

# Install dependencies
echo "Installing dependencies..."
npm install --production

# Start the application
echo "Starting the application..."
npm start

echo "Deployment completed successfully."