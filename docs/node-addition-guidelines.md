# Node Addition Guidelines

## Quick Start

Use the [Droq Node Template](https://github.com/droq-ai/dfx-base-node-template-py) to create your node, then submit a PR to add it as a Git submodule.

## Using the Template

The [Droq Node Template](https://github.com/droq-ai/dfx-base-node-template-py) provides a complete Python framework for building Droqflow nodes.

### Quick Setup with Template

```bash
# Clone the template
git clone git@github.com:droq-ai/dfx-base-node-template-py.git your-executor-node
cd your-executor-node

# Install dependencies
uv sync

# Replace src/node/main.py with your code
# Add dependencies: uv add your-package

# Configure node.json with your node information
# Test locally
PYTHONPATH=src uv run python -m node.main
```

### Template Features

- ✅ **Pre-configured structure** with essential files
- ✅ **Docker support** with ready-to-use compose file
- ✅ **Development tools** (pytest, black, ruff)
- ✅ **Documentation** and examples
- ✅ **Environment configuration** support
- ✅ **NATS integration** for messaging

## Repository Structure

```
your-executor-node/
├── node.json          # Required: Node configuration
├── src/node              # Your source code
├── pyproject.toml    # Python project configuration
├── README.md         # Node documentation
└── Dockerfile        # (Optional) Docker configuration
```

## node.json Format

```json
{
  "node_id": "your-executor-node",
  "name": "Your Executor Node",
  "description": "Brief description of what your node does",
  "version": "1.0.0",
  "api_url": "http://localhost:8000",
  "ip_address": "0.0.0.0",
  "docker_image": "your-executor-node:latest",
  "deployment_location": "local",
  "status": "active",
  "author": "Your Name/Organization",
  "components": {
    "ComponentName": "module.path.to.component",
    "description": "Another DFX component",
    "display_name": "DFX component",
    "author": "Dorq"
  }
}
```

## Required Fields

- `node_id` - Unique identifier (kebab-case)
- `name` - Human-readable name
- `description` - Brief description (1-2 sentences)
- `api_url` - Where your node service runs
- `components` - Mapping of component names to Python module paths

## Optional Fields

- `version` - Semantic version (e.g., "1.0.0")
- `docker_image` - Docker image name
- `deployment_location` - "local", "cloud", or "k8s"
- `ip_address` - Node IP address
- `status` - "active" or "inactive"
- `author` - Your name or organization

## Submission Process

1. Create your repository on GitHub
2. Add your node as a Git submodule in the Droqflow repo:
```bash
   git submodule add <gitrepo> nodes/<dfx-example-node>
   
   ```
3. Generated the node.json file using the extract script:
```bash
python3 scripts/extract_node_configs.py
 ```
4. Test your node locally
5. Submit a PR to [droq-node-registry](https://github.com/droq-ai/droq-node-registry) with:
   - Title: "Add [your-node-name] executor node"
   - Repository URL, branch/tag, and any special requirements

## API Impact

Your node will be available through:
- `GET /api/v1/nodes` - Lists all nodes including yours
- `GET /api/v1/nodes/{node_id}` - Returns details for your node
- `GET /api/v1/components/{component_class}/node` - Maps components to your node