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

## Running Locally

```bash
./start-local.sh
# run all services
./stat-all-local.sh
```

The service will start on `http://localhost:8002`.


## Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8002`)
- `LOG_LEVEL`: Logging level (default: `info`)
- `RELOAD`: Enable auto-reload (default: `true`)
- `REGISTRY_DB_PATH`: Path to SQLite database file (default: `registry.db`)

