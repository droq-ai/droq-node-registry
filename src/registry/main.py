"""Main entry point for Droq Registry Service."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn

from .api import app
from .database import bootstrap_from_assets, init_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI startup/shutdown."""
    # Startup: Initialize database and bootstrap from assets
    logger.info("Initializing registry database...")
    await init_database()
    await bootstrap_from_assets()
    logger.info("Registry database initialized and ready")
    
    yield
    
    # Shutdown: Cleanup if needed
    logger.info("Shutting down registry service...")


# Set lifespan on the app (FastAPI 0.104+ supports this)
app.router.lifespan_context = lifespan


def main():
    """Main entry point - runs the FastAPI server."""
    # Setup logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    logger.info(f"Starting Droq Registry Service on {host}:{port}")

    # Run the FastAPI server
    app_target = "registry.api:app" if reload else app
    uvicorn.run(
        app_target,
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "INFO").lower(),
    )


if __name__ == "__main__":
    main()

