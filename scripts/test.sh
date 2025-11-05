#!/bin/bash

# Run unit tests
echo "Running unit tests..."
npm test

# Capture the exit status
status=$?

if [ $status -ne 0 ]; then
  echo "Tests failed with status $status"
  exit $status
else
  echo "All tests passed successfully!"
fi