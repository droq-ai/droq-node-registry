#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "🚀 Starting Droq Ecosystem - All Services"
echo "=========================================="
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."

    # Kill services by port (most reliable)
    echo "  → Stopping services on ports 8000, 8003, 8005, 8002..."
    pkill -f "localhost:8000" 2>/dev/null || true
    pkill -f "localhost:8003" 2>/dev/null || true
    pkill -f "localhost:8005" 2>/dev/null || true
    pkill -f "localhost:8002" 2>/dev/null || true

    # Kill by service name
    pkill -f "droq-math-executor" 2>/dev/null || true
    pkill -f "langflow-executor" 2>/dev/null || true
    pkill -f "droq-registry" 2>/dev/null || true
    pkill -f "lfx-tool-executor" 2>/dev/null || true

    # Kill all background jobs from this script
    for job in $(jobs -p); do
        echo "  → Stopping background job: $job"
        kill $job 2>/dev/null || true
    done

    # Wait for all jobs to finish
    sleep 2
    wait 2>/dev/null || true

    # Final verification - force kill any remaining processes
    lsof -ti:8000,8003,8005,8002 | xargs -r kill -9 2>/dev/null || true

    echo "✅ All services stopped"
    exit 0
}

# Set trap to catch Ctrl+C and other signals
trap cleanup SIGINT SIGTERM

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed. Please install it first:"
    echo "  pipx install uv"
    echo "  or visit: https://github.com/astral-sh/uv"
    exit 1
fi

echo "📦 Starting Node Services..."
echo "---------------------------"

# Start dfx-math-executor-node (port 8003)
if [ -d "nodes/dfx-math-executor-node" ] && [ -f "nodes/dfx-math-executor-node/start-local.sh" ]; then
    echo "→ Starting dfx-math-executor-node (port 8003)..."
    cd nodes/dfx-math-executor-node
    ./start-local.sh &
    MATH_PID=$!
    cd ../..
    echo "  ✅ dfx-math-executor-node started (PID: $MATH_PID)"
else
    echo "  ⚠️  dfx-math-executor-node not found"
fi

# Wait a moment for math service to start
sleep 2

# Start lfx-runtime-executor-node (port 8000)
if [ -d "nodes/lfx-runtime-executor-node" ] && [ -f "nodes/lfx-runtime-executor-node/start-local.sh" ]; then
    echo "→ Starting lfx-runtime-executor-node (port 8000)..."
    cd nodes/lfx-runtime-executor-node
    ./start-local.sh &
    RUNTIME_PID=$!
    cd ../..
    echo "  ✅ lfx-runtime-executor-node started (PID: $RUNTIME_PID)"
else
    echo "  ⚠️  lfx-runtime-executor-node not found"
fi

# Wait a moment for runtime service to start
sleep 3

# Start lfx-tool-executor-node (port 8005)
if [ -d "nodes/lfx-tool-executor-node" ] && [ -f "nodes/lfx-tool-executor-node/start-local.sh" ]; then
    echo "→ Starting lfx-tool-executor-node (port 8005)..."
    cd nodes/lfx-tool-executor-node
    ./start-local.sh &
    TOOL_PID=$!
    cd ../..
    echo "  ✅ lfx-tool-executor-node started (PID: $TOOL_PID)"
else
    echo "  ⚠️  lfx-tool-executor-node not found"
fi

# Wait for all node services to be ready
echo ""
echo "⏳ Waiting for node services to be ready..."
sleep 5

# Test health endpoints
echo "🏥 Checking service health..."
echo "---------------------------"

if curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo "  ✅ dfx-math-executor-node (8003) - healthy"
else
    echo "  ❌ dfx-math-executor-node (8003) - not responding"
fi

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ lfx-runtime-executor-node (8000) - healthy"
else
    echo "  ❌ lfx-runtime-executor-node (8000) - not responding"
fi

if curl -s http://localhost:8005/health > /dev/null 2>&1; then
    echo "  ✅ lfx-tool-executor-node (8005) - healthy"
else
    echo "  ❌ lfx-tool-executor-node (8005) - not responding"
fi

# Install/update dependencies if needed
if [ ! -d ".venv" ] || [ ! -f "uv.lock" ]; then
    echo ""
    echo "📦 Installing registry dependencies..."
    uv sync
fi

echo ""
echo "🚀 Starting Registry Service..."
echo "-------------------------------"

# Get configuration from environment or use defaults
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8002}"
RELOAD="${RELOAD:-true}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Reload: $RELOAD"
echo "  Log Level: $LOG_LEVEL"
echo ""
echo "🎉 All services are running!"
echo "Registry: http://$HOST:$PORT"
echo "Nodes: 8000, 8003, 8005"
echo ""
echo "Press Ctrl+C to stop all services"
echo "================================"
echo ""

# Run the registry service in foreground
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8002}"
export RELOAD="${RELOAD:-true}"
export LOG_LEVEL="${LOG_LEVEL:-info}"

# Start registry service in foreground (this will be the main process)
uv run droq-registry-service

# This line will only be reached when the registry service stops