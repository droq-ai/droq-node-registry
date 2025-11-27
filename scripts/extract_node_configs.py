#!/usr/bin/env python3
"""
Extract node.json files from Git submodules and place them in assets/nodes/
"""
import json
import logging
import subprocess
import re
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_gitmodules():
    """Parse .gitmodules file to get submodule URLs"""
    gitmodules_path = Path(__file__).parent.parent / ".gitmodules"
    submodule_urls = {}

    if not gitmodules_path.exists():
        logger.warning(f".gitmodules file not found at {gitmodules_path}")
        return submodule_urls

    try:
        with open(gitmodules_path, 'r') as f:
            content = f.read()

        # Parse submodule sections
        submodule_pattern = r'\[submodule "(.*?)"\](.*?)url = (.*?)\n'
        matches = re.findall(submodule_pattern, content, re.DOTALL)

        for name, section, url in matches:
            # Extract path from the section
            path_match = re.search(r'path = (.*)', section)
            path = path_match.group(1).strip() if path_match else ""

            # Convert git@ to HTTPS URL for GitHub
            if url.startswith('git@github.com:'):
                repo_name = url.replace('git@github.com:', '').replace('.git', '')
                https_url = f"https://github.com/{repo_name}"
                submodule_urls[path] = https_url
            elif url.startswith('https://github.com/'):
                submodule_urls[path] = url.replace('.git', '')
            else:
                # Keep original URL if it's not GitHub
                submodule_urls[path] = url

    except Exception as e:
        logger.warning(f"Failed to parse .gitmodules: {e}")

    return submodule_urls

def get_git_commit_info(submodule_path):
    """Get git commit information for a submodule"""
    try:
        # Get current commit SHA
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True
        )
        current_commit = result.stdout.strip()

        # Get first commit timestamp (created_at)
        result = subprocess.run(
            ['git', 'log', '--reverse', '--format=%ct', 'HEAD'],
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True
        )
        timestamps = result.stdout.strip().split('\n')
        first_timestamp = int(timestamps[0]) if timestamps else None

        # Get last commit timestamp (updated_at)
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct', 'HEAD'],
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True
        )
        last_timestamp = int(result.stdout.strip())

        return {
            'commit': current_commit,
            'created_at': datetime.fromtimestamp(first_timestamp).isoformat() + 'Z' if first_timestamp else None,
            'updated_at': datetime.fromtimestamp(last_timestamp).isoformat() + 'Z'
        }
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to get git info for {submodule_path}: {e}")
        return {
            'commit': None,
            'created_at': None,
            'updated_at': None
        }

def extract_node_configs():
    """Extract node.json from each submodule to assets/nodes/"""
    # Get the registry root directory (assuming script is in scripts/ subdirectory)
    registry_root = Path(__file__).parent.parent
    nodes_dir = registry_root / "nodes"
    assets_dir = registry_root / "assets" / "nodes"

    # Parse .gitmodules to get repository URLs
    submodule_urls = parse_gitmodules()
    logger.info(f"Found {len(submodule_urls)} submodule URLs")

    logger.info(f"Registry root: {registry_root}")
    logger.info(f"Nodes directory: {nodes_dir}")
    logger.info(f"Assets directory: {assets_dir}")

    # Ensure assets directory exists
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing configs
    existing_files = list(assets_dir.glob("*.json"))
    if existing_files:
        for json_file in existing_files:
            json_file.unlink()

    extracted_count = 0
    node_id_to_submodule = {}

    # Process each submodule directory
    if not nodes_dir.exists():
        logger.error(f"Nodes directory not found: {nodes_dir}")
        logger.info("Please ensure Git submodules are initialized with: git submodule update --init --recursive")
        return extracted_count

    submodule_dirs = [d for d in nodes_dir.iterdir() if d.is_dir()]
    logger.info(f"Found {len(submodule_dirs)} submodule directories")

    for submodule_dir in submodule_dirs:
        logger.info(f"Processing submodule: {submodule_dir.name}")

        node_json_path = submodule_dir / "node.json"
        if not node_json_path.exists():
            logger.warning(f"No node.json found in {submodule_dir.name}")
            continue

        try:
            # Read and validate node.json
            with open(node_json_path, 'r') as f:
                node_config = json.load(f)

            # Validate required fields
            if 'node_id' not in node_config:
                logger.error(f"node.json in {submodule_dir.name} missing node_id")
                continue

            node_id = node_config['node_id']
            logger.info(f"Found node configuration for: {node_id}")

            # Update source_code_location to point to submodule
            node_config['source_code_location'] = str(submodule_dir.relative_to(registry_root))

            # Get repository URL from .gitmodules
            submodule_path = str(submodule_dir.relative_to(registry_root))
            repository_url = submodule_urls.get(submodule_path)
            if repository_url:
                node_config['repository_url'] = repository_url
                logger.info(f"Added repository URL: {repository_url}")
            else:
                logger.warning(f"No repository URL found for {submodule_path}")

            # Add category with default value
            if 'category' not in node_config:
                node_config['category'] = 'droq-core'

            # Get git commit information
            git_info = get_git_commit_info(submodule_dir)

            # Add git information to node config
            if git_info['commit']:
                node_config['commit'] = git_info['commit']
            if git_info['created_at']:
                node_config['created_at'] = git_info['created_at']
            if git_info['updated_at']:
                node_config['updated_at'] = git_info['updated_at']

            # Check for node_id conflicts and use submodule directory name as filename
            output_filename = f"{node_id}.json"
            if node_id in node_id_to_submodule:
                logger.warning(f"Node ID conflict detected: {node_id} exists in multiple submodules")
                logger.warning(f"Using submodule directory name as filename to avoid conflicts")
                output_filename = f"{submodule_dir.name}.json"
            else:
                node_id_to_submodule[node_id] = submodule_dir.name

            # Write to assets/nodes
            output_path = assets_dir / output_filename
            with open(output_path, 'w') as f:
                json.dump(node_config, f, indent=2)

            logger.info(f"Extracted {node_id} from {submodule_dir.name} -> {output_path}")
            extracted_count += 1

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {submodule_dir.name}/node.json: {e}")
        except Exception as e:
            logger.error(f"Failed to extract from {submodule_dir.name}: {e}")
            continue

    logger.info(f"Extraction complete: {extracted_count} node configurations extracted")
    return extracted_count

if __name__ == "__main__":
    try:
        count = extract_node_configs()
        if count > 0:
            print(f"✅ Successfully extracted {count} node configuration(s)")
        else:
            print("⚠️  No node configurations extracted. Check submodules are initialized.")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        exit(1)