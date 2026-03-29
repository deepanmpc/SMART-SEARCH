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
pyinstaller src/api.py --onefile --distpath launcher/backend --name api --log-level WARN

echo "2. Installing Launcher Dependencies..."
cd launcher
npm install

echo "3. Packaging Electron App with electron-builder..."
# Build distributable installers (.dmg, .exe, .AppImage)
npm run build

echo "====================================="
echo " Build successful! Output is in launcher/dist"
echo " Look for .dmg (macOS), .exe (Windows), .AppImage (Linux)"
echo "====================================="
