#!/bin/bash
# Project Reality Mortar Calculator - Linux/Mac Launcher
# Run this script to start the calculator: ./run.sh

set -e  # Exit on error

echo "===================================="
echo "PR MORTAR CALCULATOR - Starting..."
echo "===================================="
echo ""

# Change to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Trap Ctrl+C for graceful shutdown
trap ctrl_c INT
function ctrl_c() {
    echo ""
    echo ""
    echo "===================================="
    echo "Server stopped."
    echo "You can close this terminal."
    echo "===================================="
    echo ""
    exit 0
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Try to detect Python installation
if command_exists python3; then
    echo "Found Python via python3 command"
    python3 calculator/server.py
elif command_exists python; then
    echo "Found Python via python command"
    python calculator/server.py
else
    # Python not found - show error message
    echo ""
    echo "===================================="
    echo "ERROR: Python not found"
    echo "===================================="
    echo ""
    echo "Python 3.8 or newer is required to run this calculator."
    echo ""
    echo "Please install Python:"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  - macOS: brew install python3"
    echo "  - Or download from: https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# Server stopped - clean exit
echo ""
echo "===================================="
echo "Server stopped."
echo "You can close this terminal."
echo "===================================="
echo ""
