"""Database layer for Droq Registry Service using SQLite as key-value store."""

import aiosqlite
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.getenv("REGISTRY_DB_PATH", "registry.db")


async def get_db_connection() -> aiosqlite.Connection:
    """Get database connection."""
    db_path = Path(DB_PATH)
    if not db_path.is_absolute():
        # Make relative to registry service root
        registry_root = Path(__file__).parent.parent.parent
        db_path = registry_root / DB_PATH

    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    return conn


async def init_database():
    """Initialize database schema."""
    conn = await get_db_connection()
    try:
        # Nodes table: stores node metadata
        await conn.execute("""
                           CREATE TABLE IF NOT EXISTS nodes (
                                                                node_id TEXT PRIMARY KEY,
                                                                name TEXT NOT NULL,
                                                                description TEXT,
                                                                source_code_location TEXT,
                                                                docker_image TEXT,
                                                                deployment_location TEXT NOT NULL,
                                                                api_url TEXT,
                                                                ip_address TEXT,
                                                                status TEXT NOT NULL DEFAULT 'active',
                                                                metadata_json TEXT,
                                                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                           """)

        # Components table: stores component mappings for each node
        await conn.execute("""
                           CREATE TABLE IF NOT EXISTS components (
                                                                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                     node_id TEXT NOT NULL,
                                                                     component_class TEXT NOT NULL,
                                                                     module_path TEXT NOT NULL,
                                                                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                     UNIQUE(node_id, component_class),
                               FOREIGN KEY (node_id) REFERENCES nodes(node_id) ON DELETE CASCADE
                               )
                           """)

        # Indexes for faster lookups
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_components_node_id ON components(node_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_components_class ON components(component_class)")

        await conn.commit()
        logger.info("Database schema initialized")
    finally:
        await conn.close()


async def bootstrap_from_assets():
    """Bootstrap database from JSON files in assets/nodes directory."""
    registry_root = Path(__file__).parent.parent.parent
    assets_dir = registry_root / "assets" / "nodes"

    if not assets_dir.exists():
        logger.warning(f"Assets directory not found: {assets_dir}")
        return

    # Find all JSON files in assets/nodes
    json_files = list(assets_dir.glob("*.json"))

    if not json_files:
        logger.warning(f"No JSON files found in {assets_dir}")
        return

    logger.info(f"Bootstrapping database from {len(json_files)} node configuration files")

    conn = await get_db_connection()
    try:
        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    node_config = json.load(f)

                node_id = node_config.get("node_id")
                if not node_id:
                    logger.warning(f"Node config {json_file} missing node_id, skipping")
                    continue

                # Insert or update node metadata
                await conn.execute("""
                    INSERT OR REPLACE INTO nodes (
                        node_id, name, description, source_code_location,
                        docker_image, deployment_location, api_url, ip_address, status, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id,
                    node_config.get("name", ""),
                    node_config.get("description", ""),
                    node_config.get("source_code_location"),
                    node_config.get("docker_image"),
                    node_config.get("deployment_location", "local"),
                    node_config.get("api_url"),
                    node_config.get("ip_address"),
                    node_config.get("status", "active"),
                    json.dumps(node_config),  # Store full config as JSON for flexibility
                ))

                # Load components from node config (either from "components" key or "components_json_path")
                components_map = {}

                # First, try to get components directly from the config
                if "components" in node_config:
                    components_map = node_config["components"]
                    logger.info(f"Loaded {len(components_map)} components directly from node config for {node_id}")
                # Fallback to loading from components_json_path (for backward compatibility)
                elif "components_json_path" in node_config:
                    components_json_path = node_config.get("components_json_path")
                    components_map = await load_components_json(components_json_path)
                    logger.info(f"Loaded {len(components_map)} components from {components_json_path} for node {node_id}")
                else:
                    logger.warning(f"No components or components_json_path found for node {node_id}")

                if components_map:
                    # Delete existing components for this node
                    await conn.execute("DELETE FROM components WHERE node_id = ?", (node_id,))

                    # Insert components
                    for component_class, module_path in components_map.items():
                        await conn.execute("""
                            INSERT OR REPLACE INTO components (node_id, component_class, module_path)
                            VALUES (?, ?, ?)
                        """, (node_id, component_class, module_path))

                    logger.info(f"Inserted {len(components_map)} components into database for node {node_id}")

            except Exception as e:
                logger.error(f"Failed to bootstrap node from {json_file}: {e}")
                continue

        await conn.commit()
        logger.info("Database bootstrap completed")
    finally:
        await conn.close()


async def load_components_json(components_json_path: str) -> dict[str, str]:
    """Load components.json file and return component mapping.

    Args:
        components_json_path: Path to components.json file (relative to droq root or absolute)

    Returns:
        Dictionary mapping component_class -> module_path
    """
    # Try multiple path resolution strategies
    paths_to_try = []

    # 1. If absolute path, use as-is
    if os.path.isabs(components_json_path):
        paths_to_try.append(Path(components_json_path))
    else:
        # 2. Relative to registry service root
        registry_root = Path(__file__).parent.parent.parent
        paths_to_try.append(registry_root / components_json_path)

        # 3. Relative to droq root (../nodes/...)
        droq_root = registry_root.parent
        paths_to_try.append(droq_root / components_json_path)

        # 4. Relative to current working directory
        paths_to_try.append(Path(components_json_path))

    full_path = None
    for path in paths_to_try:
        if path.exists():
            full_path = path
            break

    if not full_path or not full_path.exists():
        logger.warning(f"components.json not found. Tried paths: {[str(p) for p in paths_to_try]}")
        return {}

    try:
        with open(full_path, "r") as f:
            components_map = json.load(f)
        logger.info(f"Loaded {len(components_map)} components from {full_path}")
        return components_map
    except Exception as e:
        logger.error(f"Failed to load components.json from {full_path}: {e}")
        return {}


async def get_all_nodes() -> list[dict[str, Any]]:
    """Get all nodes from database."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM nodes WHERE status = 'active'")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_node(node_id: str) -> dict[str, Any] | None:
    """Get a specific node from database."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_node_components(node_id: str) -> dict[str, str]:
    """Get component mapping for a specific node.

    Returns:
        Dictionary mapping component_class -> module_path
    """
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT component_class, module_path FROM components WHERE node_id = ?",
            (node_id,)
        )
        rows = await cursor.fetchall()
        return {row["component_class"]: row["module_path"] for row in rows}
    finally:
        await conn.close()


async def get_node_supported_components(node_id: str) -> list[str]:
    """Get list of supported component class names for a node."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT component_class FROM components WHERE node_id = ? ORDER BY component_class",
            (node_id,)
        )
        rows = await cursor.fetchall()
        return [row["component_class"] for row in rows]
    finally:
        await conn.close()


async def get_node_by_component(component_class: str) -> dict[str, Any] | None:
    """Get node information for a specific component class.

    Args:
        component_class: Name of the component class (e.g., "TextInputComponent")

    Returns:
        Dictionary with node metadata and component mapping, or None if not found
    """
    conn = await get_db_connection()
    try:
        # First, find which node supports this component and get the module path
        cursor = await conn.execute(
            """
            SELECT c.node_id, c.module_path
            FROM components c
                     INNER JOIN nodes n ON c.node_id = n.node_id
            WHERE c.component_class = ? AND n.status = 'active'
                LIMIT 1
            """,
            (component_class,)
        )
        row = await cursor.fetchone()

        if not row:
            logger.warning(f"Component '{component_class}' not found in any active node")
            return None

        node_id = row["node_id"]
        module_path = row["module_path"]

        # Get the full node information
        node_dict = await get_node(node_id)
        if not node_dict:
            logger.warning(f"Node '{node_id}' not found (component '{component_class}' references it)")
            return None

        # Get all components for this node
        components_map = await get_node_components(node_id)

        return {
            "node": node_dict,
            "components": components_map,
            "module_path": module_path,  # Module path for this specific component
        }
    finally:
        await conn.close()
