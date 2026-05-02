#!/bin/bash
# Generate a pairing token for a new device.
# Usage: ./generate-token.sh --device-name "My Laptop"
set -euo pipefail

INSTALL_DIR="${ADBOX_INSTALL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV="$INSTALL_DIR/server/.venv"
ENV_FILE="$INSTALL_DIR/.env"

if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
elif [ -f "$VENV/Scripts/activate" ]; then
    source "$VENV/Scripts/activate"
fi

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

python3 "$INSTALL_DIR/scripts/generate-token.py" "$@" \
    --env-file "$ENV_FILE"
