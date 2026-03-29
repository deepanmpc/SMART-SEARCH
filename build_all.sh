#!/bin/bash
set -e

echo "====================================="
echo " Building SMART SEARCH Cross-Platform"
echo "====================================="

# Ensure virtual env is used
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found. Please create one at .venv"
    exit 1
fi

echo "1. Building Python Backend with PyInstaller..."
# We output the executable into launcher/backend so electron-builder can bundle it
pyinstaller src/api.py --onefile --distpath launcher/backend --log-level WARN

echo "2. Installing Launcher Dependencies..."
cd launcher
npm install

echo "3. Packaging Electron App with electron-builder..."
# Notice we added extraResources in package.json to pack the launcher/backend folder into the app
npm run pack

echo "====================================="
echo " Build successful! Output is in launcher/dist"
echo "====================================="
