# Droq Registry Service

Registry service for mapping executor nodes to their supported components.

## Overview

The Droq Registry Service maintains a mapping of executor nodes to their metadata and supported components. It uses a SQLite database as a key-value store, bootstrapped from JSON configuration files in the `assets/nodes/` directory.

## Features

- **Key-Value Store**: SQLite database for storing node metadata and component mappings
- **Asset-Based Configuration**: Node configurations stored as JSON files in `assets/nodes/`
- **Automatic Bootstrap**: Database is automatically initialized and populated from assets on startup
- **Component Mapping**: Loads `components.json` from each node to know which components each node supports
- **RESTful API**: Provides endpoints to query nodes and their components

## Architecture

- **Database**: SQLite (`registry.db`) with two tables:
  - `nodes`: Stores node metadata
  - `components`: Stores component mappings (component_class -> module_path) for each node
- **Assets**: JSON files in `assets/nodes/` define node configurations
- **Bootstrap**: On startup, the service reads all JSON files from `assets/nodes/` and populates the database

## Adding a New Node

1. Create a JSON file in `assets/nodes/` (e.g., `assets/nodes/droq-executor-node.json`):
```json
{
  "node_id": "droq-executor-node",
  "name": "Droq Executor Node",
  "description": "Executor node for Droq-specific components",
  "source_code_location": "../nodes/droq-executor-node",
  "docker_image": "droq-executor-node:latest",
  "deployment_location": "local",
  "api_url": "http://localhost:8001",
  "ip_address": "127.0.0.1",
  "status": "active",
  "components": {
    "MultiplyComponent": "droq.components.math.multiply",
    ...
  }
}
```

2. Restart the service - it will automatically bootstrap the new node from the JSON file

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
```

The service will start on `http://localhost:8002`.

## Running with Docker

```bash
docker compose up -d
```

## Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8002`)
- `LOG_LEVEL`: Logging level (default: `info`)
- `RELOAD`: Enable auto-reload (default: `true`)
- `REGISTRY_DB_PATH`: Path to SQLite database file (default: `registry.db`)

