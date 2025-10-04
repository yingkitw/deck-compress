#!/bin/bash

# Create necessary directories
mkdir -p static/uploads
mkdir -p templates

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
