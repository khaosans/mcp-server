#!/bin/bash

# Kill any existing server processes
pkill -f "uvicorn|python.*main:app" && lsof -ti :8080 | xargs kill -9 2>/dev/null || true

# Start the server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8080 --reload 