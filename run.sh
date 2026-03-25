#!/bin/bash

# Port for FastAPI
API_PORT=8000

echo "🚀 Starting SMART-SEARCH Spotlight AI Launcher..."

# 1. Start the FastAPI backend
echo "📦 Starting Backend (FastAPI) on port $API_PORT..."
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
.venv/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port $API_PORT --app-dir src > backend.log 2>&1 &
BACKEND_PID=$!
trap "kill $BACKEND_PID" EXIT

# Wait for backend to be ready
echo "⏳ Waiting for backend to initialize..."
MAX_RETRIES=10
COUNT=0
while ! curl -s http://localhost:$API_PORT/stats > /dev/null; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Backend failed to start. Check backend.log"
        kill $BACKEND_PID
        exit 1
    fi
done
echo "✅ Backend is up!"

# 2. Start the Electron frontend
echo "🖥️ Starting Frontend (Electron)..."
cd launcher
npm start
