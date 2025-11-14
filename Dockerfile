FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY assets/ ./assets/

# Install dependencies
RUN uv sync --frozen

# Expose port
EXPOSE 8002

# Run the service
CMD ["uv", "run", "droq-registry-service"]

