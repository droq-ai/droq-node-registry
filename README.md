# Droq Registry Service

Registry service for mapping executor nodes to their supported components.

## Overview

The Droq Registry Service maintains a mapping of executor nodes to their metadata and supported components. It uses Git submodules for node management and a SQLite database as a key-value store, automatically bootstrapped from extracted JSON configurations.

## Features

- **Git Submodule Management**: Nodes managed as Git submodules under `/nodes/`
- **Automatic Configuration Extraction**: Extracts `node.json` files from submodules to `assets/nodes/`
- **Key-Value Store**: SQLite database for storing node metadata and component mappings
- **Automatic Bootstrap**: Database is automatically initialized and populated from extracted configurations on startup
- **Component Mapping**: Tracks which components each node supports
- **RESTful API**: Provides endpoints to query nodes and their components

## Architecture

- **Git Submodules**: Node repositories stored in `/nodes/` directory as Git submodules
- **Configuration Extraction**: Scripts extract `node.json` from each submodule to `assets/nodes/`
- **Database**: SQLite (`registry.db`) with two tables:
  - `nodes`: Stores node metadata
  - `components`: Stores component mappings (component_class -> module_path) for each node
- **Assets**: Generated JSON files in `assets/nodes/` define node configurations (auto-extracted from submodules)
- **Bootstrap**: On startup, the service reads all JSON files from `assets/nodes/` and populates the database

## Adding a New Node

📖 **See [docs/node-addition-guidelines.md](docs/node-addition-guidelines.md)** for complete instructions on adding new executor nodes to the registry.

**Quick Summary:**
- Create repository with `node.json` configuration
- Submit PR to add as Git submodule
- Registry automatically extracts and integrates your node

## API Endpoints

### `GET /api/v1/nodes`
Returns list of all active executor nodes with their metadata and component counts.

### `GET /api/v1/nodes/{node_id}`
Returns detailed information about a specific node, including full component mapping.

### `GET /api/v1/components/{component_class}/node`
Returns the executor node that handles a specific component class.

**Example:**
```bash
curl http://localhost:8002/api/v1/components/TextInputComponent/node
```

**Response:**
```json
{
  "node": {
    "node_id": "langflow-executor-node",
    "name": "Langflow Executor Node",
    "api_url": "http://localhost:8000",
    "ip_address": "127.0.0.1",
    ...
  },
  "components": {...},
  "module_path": "lfx.components.input_output.text"
}
```

**Response:**
```json
{
  "nodes": [
    {
      "metadata": {
        "node_id": "langflow-executor-node",
        "name": "Langflow Executor Node",
        "description": "...",
        "source_code_location": "../nodes/langflow-executor-node",
        "docker_image": "langflow-executor-node:latest",
        "deployment_location": "local",
        "api_url": "http://localhost:8000",
        "status": "active",
        "supported_components": ["TextInputComponent", "ChatInput", ...]
      },
      "components_count": 348
    }
  ],
  "total_nodes": 1
}
```

### `GET /api/v1/nodes/{node_id}`
Returns detailed information about a specific node, including full component mapping.

**Response:**
```json
{
  "node": {
    "node_id": "langflow-executor-node",
    "name": "Langflow Executor Node",
    "description": "...",
    "source_code_location": "../nodes/langflow-executor-node",
    "docker_image": "langflow-executor-node:latest",
    "deployment_location": "local",
    "api_url": "http://localhost:8000",
    "status": "active",
    "supported_components": ["TextInputComponent", "ChatInput", ...]
  },
  "components": {
    "TextInputComponent": "lfx.components.input_output.text",
    "ChatInput": "lfx.components.input_output.chat",
    ...
  }
}
```

## Database

The service uses SQLite as a key-value store. The database file (`registry.db`) is created automatically on first startup. You can customize the database path using the `REGISTRY_DB_PATH` environment variable.

### Database Schema

**nodes table:**
- `node_id` (PRIMARY KEY): Unique identifier for the node
- `name`: Display name
- `description`: Node description
- `source_code_location`: Path to source code
- `docker_image`: Docker image name
- `deployment_location`: "local" | "cloud" | "k8s"
- `api_url`: API endpoint URL
- `status`: "active" | "inactive" | "deploying"
- `metadata_json`: Full JSON configuration (for flexibility)
- `created_at`, `updated_at`: Timestamps

**components table:**
- `id` (PRIMARY KEY): Auto-increment ID
- `node_id` (FOREIGN KEY): References nodes.node_id
- `component_class`: Component class name
- `module_path`: Python module path
- `created_at`: Timestamp
- UNIQUE constraint on (node_id, component_class)

## Development

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Git (for submodule operations)

### Quick Start

```bash
# Clone and setup
git clone --recurse-submodules https://github.com/droq-ai/droq-node-registry
cd droq-node-registry
make setup

# Start the service
make start
```

The service will start on `http://localhost:8002`.

### Development Commands

```bash
# Initial setup with submodules and dependencies
make setup

# Start the registry service locally
make start

# Extract configurations from submodules
make extract-configs

# Update submodules from remote
make update-submodules

# Update submodules and extract configurations
make refresh

# Check project status
make status

# Clean generated files
make clean

# Reset database
make reset-db
```

### Manual Development

```bash
# Install dependencies
uv sync

# Initialize/update submodules
git submodule update --init --recursive

# Extract node configurations
uv run python scripts/extract_node_configs.py

# Start the service
./start-local.sh
```

## Running with Docker

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f registry

# Stop services
docker compose down
```

## Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8002`)
- `LOG_LEVEL`: Logging level (default: `info`)
- `RELOAD`: Enable auto-reload (default: `true`)
- `REGISTRY_DB_PATH`: Path to SQLite database file (default: `registry.db`)

## Directory Structure

```
droq-node-registry/
├── nodes/                    # Git submodules (executor nodes)
│   ├── dfx-math-executor-node/
│   ├── lfx-runtime-executor-node/
│   └── lfx-tool-executor-node/
├── scripts/                  # Management scripts
│   ├── extract_node_configs.py
│   └── update_submodules.py
├── assets/nodes/            # Generated configurations (auto-extracted)
├── src/registry/            # Registry service code
├── docker-compose.yml       # Docker configuration
├── Makefile                # Development automation
└── start-local.sh          # Development startup script
```

## Maintenance

### Updating Existing Nodes

To update an existing node to a new version:

1. Update the submodule to the desired commit/tag:
   ```bash
   cd nodes/your-executor-node
   git pull origin main
   cd ../..
   git add nodes/your-executor-node
   git commit -m "Update your-executor-node to latest version"
   ```

2. Extract new configurations:
   ```bash
   make extract-configs
   ```

3. Test and deploy:
   ```bash
   make start
   ```

### Removing Nodes

To remove a node from the registry:

1. Remove the submodule:
   ```bash
   git submodule deinit nodes/your-executor-node
   git rm nodes/your-executor-node
   ```

2. Commit the changes

3. Clean up generated files:
   ```bash
   make clean
   make extract-configs
   ```

