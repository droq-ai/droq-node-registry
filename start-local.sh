#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Starting Droq Registry Service locally..."
echo ""

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed. Please install it first:"
    echo "  pipx install uv"
    echo "  or visit: https://github.com/astral-sh/uv"
    exit 1
fi

# Install/update dependencies if needed
if [ ! -d ".venv" ] || [ ! -f "uv.lock" ]; then
    echo "Installing dependencies..."
    uv sync
fi

# Get configuration from environment or use defaults
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Reload: $RELOAD"
echo "  Log Level: $LOG_LEVEL"
echo ""
echo "Starting registry service on http://$HOST:$PORT"
echo "Press Ctrl+C to stop"
echo ""

if [ "$RELOAD" = "true" ]; then
    # Use import string for reload mode
    uv run uvicorn registry.main:app --host $HOST --port $PORT --reload --log-level $LOG_LEVEL
else
    uv run droq-registry-service
fi

