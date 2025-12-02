#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "🚀 Starting Droqflow Nodes"
echo "=========================================="
echo ""

# Global variables for tracking services
ALL_PORTS=()
ALL_PIDS=()

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."

    # Kill services by discovered ports
    if [ ${#ALL_PORTS[@]} -gt 0 ]; then
        echo "  → Stopping services on ports: ${ALL_PORTS[*]}..."
        for port in "${ALL_PORTS[@]}"; do
            pkill -f "localhost:$port" 2>/dev/null || true
        done
    fi

    # Kill registry service
    pkill -f "droq-registry" 2>/dev/null || true

    # Kill all background jobs from this script
    for job in $(jobs -p); do
        echo "  → Stopping background job: $job"
        kill $job 2>/dev/null || true
    done

    # Wait for all jobs to finish
    sleep 2
    wait 2>/dev/null || true

    # Final verification - force kill any remaining processes
    if [ ${#ALL_PORTS[@]} -gt 0 ]; then
        ports_str=$(IFS=,; echo "${ALL_PORTS[*]}")
        lsof -ti:$ports_str | xargs -r kill -9 2>/dev/null || true
    fi

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

# Function to find an available port
find_available_port() {
    local start_port=8000
    local end_port=8100

    for ((port=$start_port; port<=$end_port; port++)); do
        if ! lsof -ti:$port >/dev/null 2>&1; then
            echo "$port"
            return
        fi
    done

    echo "8001"  # fallback if no ports available
}

# Function to extract port from a node directory
extract_port() {
    local node_dir="$1"

    # Try to find port in common configuration files
    for file in "$node_dir"/{start-local.sh,pyproject.toml,config.yaml,config.json,settings.py,.env}; do
        if [ -f "$file" ]; then
            port=$(grep -oP 'port[:\s=]+\K[0-9]+' "$file" 2>/dev/null | head -1 || true)
            if [ -n "$port" ]; then
                echo "$port"
                return
            fi
        fi
    done

    # Find the first available port dynamically
    find_available_port
}

# Function to start a node service
start_node() {
    local node_dir="$1"
    local node_name=$(basename "$node_dir")

    if [ -f "$node_dir/start-local.sh" ]; then
        local port=$(extract_port "$node_dir")
        ALL_PORTS+=("$port")

        echo "→ Starting $node_name (port $port)..."
        cd "$node_dir"
        ./start-local.sh &
        local pid=$!
        cd ../..

        ALL_PIDS+=("$pid")
        echo "  ✅ $node_name started (PID: $pid)"

        return 0
    else
        echo "  ⚠️  $node_name not found (missing start-local.sh)"
        return 1
    fi
}

# Discover and start all node services
if [ -d "nodes" ]; then
    for node_dir in nodes/*/; do
        if [ -d "$node_dir" ]; then
            start_node "$node_dir"
            sleep 1  # Small delay between startups
        fi
    done
else
    echo "❌ No nodes directory found"
    exit 1
fi

# Wait for all node services to be ready
echo ""
echo "⏳ Waiting for node services to be ready..."
sleep 5

# Test health endpoints dynamically
echo "🏥 Checking service health..."
echo "---------------------------"

for port in "${ALL_PORTS[@]}"; do
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "  ✅ Node (port $port) - healthy"
    else
        echo "  ❌ Node (port $port) - not responding"
    fi
done

# Install/update dependencies if needed
if [ ! -d ".venv" ] || [ ! -f "uv.lock" ]; then
    echo ""
    echo "📦 Installing registry dependencies..."
    uv sync
fi

# Add registry port
ALL_PORTS+=("8000")

echo ""
echo "🚀 Starting Registry Service..."
echo "-------------------------------"

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
echo "🎉 All services are running!"
echo "Registry: http://$HOST:$PORT"
echo "Nodes: ${ALL_PORTS[*]%,8000}"  # Remove registry port from nodes list
echo ""
echo "Press Ctrl+C to stop all services"
echo "================================"
echo ""

# Run the registry service in foreground
export HOST="$HOST"
export PORT="$PORT"
export RELOAD="$RELOAD"
export LOG_LEVEL="$LOG_LEVEL"

# Start registry service in background to track its PID
./start-local.sh &
REGISTRY_PID=$!

# Wait for all background services to keep the script alive
# This will wait until any service fails or Ctrl+C is pressed
wait