"""FastAPI application for Droq Registry Service."""

import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .database import (
    get_all_nodes,
    get_node,
    get_node_components,
    get_node_supported_components,
    get_node_by_component,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Droq Registry Service",
    description="Registry service for mapping executor nodes to their supported components",
    version="0.1.0",
)


class NodeMetadata(BaseModel):
    """Metadata about an executor node."""

    node_id: str
    name: str
    description: str
    source_code_location: str | None = None
    docker_image: str | None = None
    deployment_location: str  # "local" | "cloud" | "k8s"
    api_url: str | None = None  # Where the node is running (e.g., "http://localhost:8000")
    ip_address: str | None = None  # IP address of the executor node
    status: str = "active"  # "active" | "inactive" | "deploying"
    supported_components: list[str] = []  # List of component class names


class NodeInfo(BaseModel):
    """Information about a single node."""

    metadata: NodeMetadata
    components_count: int


class NodesListResponse(BaseModel):
    """Response for getNodes endpoint."""

    nodes: list[NodeInfo]
    total_nodes: int


class NodeResponse(BaseModel):
    """Response for getNode endpoint."""

    node: NodeMetadata
    components: dict[str, str]  # component_class -> module_path mapping


class ComponentNodeResponse(BaseModel):
    """Response for getNodeByComponent endpoint."""

    node: NodeMetadata
    components: dict[str, str]  # component_class -> module_path mapping
    module_path: str | None = None  # Module path for the specific component queried




@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "droq-registry-service",
        "version": "0.1.0",
        "description": "Registry service for mapping executor nodes to their supported components",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "droq-registry-service"}


@app.get("/api/v1/nodes", response_model=NodesListResponse)
async def get_nodes():
    """Get list of all active executor nodes.
    
    Returns:
        List of nodes with their metadata and component counts
    """
    db_nodes = await get_all_nodes()
    nodes = []
    
    for db_node in db_nodes:
        try:
            node_id = db_node["node_id"]
            supported_components = await get_node_supported_components(node_id)
            
            # Parse metadata_json if available, otherwise use direct fields
            metadata_dict = {}
            if db_node.get("metadata_json"):
                try:
                    metadata_dict = json.loads(db_node["metadata_json"])
                except Exception:
                    pass
            
            # Build NodeMetadata from database row
            metadata = NodeMetadata(
                node_id=db_node["node_id"],
                name=db_node["name"],
                description=db_node.get("description", ""),
                source_code_location=db_node.get("source_code_location"),
                docker_image=db_node.get("docker_image"),
                deployment_location=db_node["deployment_location"],
                api_url=db_node.get("api_url"),
                ip_address=db_node.get("ip_address"),
                status=db_node["status"],
                supported_components=supported_components,
            )
            
            nodes.append(
                NodeInfo(
                    metadata=metadata,
                    components_count=len(supported_components),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to load node {db_node.get('node_id', 'unknown')}: {e}")
            continue
    
    return NodesListResponse(nodes=nodes, total_nodes=len(nodes))


@app.get("/api/v1/nodes/{node_id}", response_model=NodeResponse)
async def get_node_endpoint(node_id: str):
    """Get detailed information about a specific executor node.
    
    Args:
        node_id: ID of the node to get information for
        
    Returns:
        Node metadata and full component mapping (component_class -> module_path)
        
    Raises:
        HTTPException: If node not found
    """
    from .database import get_node as get_node_from_db
    db_node = await get_node_from_db(node_id)
    
    if not db_node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in registry")
    
    # Get components mapping from database
    components_map = await get_node_components(node_id)
    supported_components = list(components_map.keys())
    
    # Parse metadata_json if available, otherwise use direct fields
    metadata_dict = {}
    if db_node.get("metadata_json"):
        try:
            metadata_dict = json.loads(db_node["metadata_json"])
        except Exception:
            pass
    
    # Build NodeMetadata from database row
    metadata = NodeMetadata(
        node_id=db_node["node_id"],
        name=db_node["name"],
        description=db_node.get("description", ""),
        source_code_location=db_node.get("source_code_location"),
        docker_image=db_node.get("docker_image"),
        deployment_location=db_node["deployment_location"],
        api_url=db_node.get("api_url"),
        ip_address=db_node.get("ip_address"),
        status=db_node["status"],
        supported_components=supported_components,
    )
    
    return NodeResponse(
        node=metadata,
        components=components_map,  # Full mapping: component_class -> module_path
    )


@app.get("/api/v1/components/{component_class}/node", response_model=ComponentNodeResponse)
async def get_node_by_component_endpoint(component_class: str):
    """Get the executor node that handles a specific component class.
    
    Args:
        component_class: Name of the component class (e.g., "TextInputComponent")
        
    Returns:
        Node metadata and component mapping for the node that supports this component
        
    Raises:
        HTTPException: If component not found in any node
    """
    logger.info(f"Looking up node for component '{component_class}'")
    result = await get_node_by_component(component_class)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Component '{component_class}' not found in any executor node"
        )
    
    db_node = result["node"]
    components_map = result["components"]
    module_path = result.get("module_path")
    supported_components = list(components_map.keys())
    
    # Build NodeMetadata from database row
    metadata = NodeMetadata(
        node_id=db_node["node_id"],
        name=db_node["name"],
        description=db_node.get("description", ""),
        source_code_location=db_node.get("source_code_location"),
        docker_image=db_node.get("docker_image"),
        deployment_location=db_node["deployment_location"],
        api_url=db_node.get("api_url"),
        ip_address=db_node.get("ip_address"),
        status=db_node["status"],
        supported_components=supported_components,
    )
    
    return ComponentNodeResponse(
        node=metadata,
        components=components_map,
        module_path=module_path,
    )

