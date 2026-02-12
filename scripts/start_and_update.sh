#!/bin/bash

# Navigate to the repository directory
# Ensure this path matches the location on your Raspberry Pi
CDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Assuming script is in scripts/ folder, go up one level to root
ROOT_DIR="$(dirname "$CDIR")"
cd "$ROOT_DIR" || exit

echo "Checking for updates..."
# Pull latest changes
git pull origin main

# Check exit code
if [ $? -eq 0 ]; then
    echo "Updates pulled successfully."
else
    echo "Git pull failed. Proceeding with existing code."
fi

# Optional: Install requirements if they changed (uncomment if desired)
# pip install -r requirements.txt

echo "Starting Discord Bots..."
python3 main.py
