FROM python:3.11-slim

# Install git for submodule operations
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY .gitmodules ./.gitmodules

# Copy current assets (may be empty initially)
COPY assets/ ./assets/

# Install dependencies
RUN uv sync --frozen

# Expose port
EXPOSE 8002

# Run the service
CMD ["uv", "run", "droq-registry-service"]

