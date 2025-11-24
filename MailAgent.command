#!/bin/bash
set -e

# Resolve repository root no matter where the script is run from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Bootstrap the virtual environment on first run so friends don't have to
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment and installing dependencies..."
  make setup
fi

# Launch the interactive mail agent
make mail
