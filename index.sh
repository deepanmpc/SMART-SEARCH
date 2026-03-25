#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./index.sh <path_to_file_or_folder>"
    exit 1
fi

TARGET_PATH="$1"

echo "📂 Indexing: $TARGET_PATH"

# Ensure src is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Run the existing indexing logic via the CLI
.venv/bin/python3 src/main.py index "$TARGET_PATH"
