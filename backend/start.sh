#!/bin/bash

# Kill any existing server processes
pkill -f "uvicorn|python.*main:app" && lsof -ti :8080 | xargs kill -9 2>/dev/null || true

# Create logs directory if it doesn't exist
mkdir -p logs

# Get current timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/server_${TIMESTAMP}.log"

echo "🚀 Starting MCP Server..."
echo "📝 Logging to: ${LOG_FILE}"

# Start the server with proper Python path
PYTHONPATH=$PYTHONPATH:$(pwd)/.. poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload 2>&1 | tee "${LOG_FILE}" 