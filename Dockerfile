# HelixOps production Docker image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd -m -u 1000 helixops && chown -R helixops:helixops /app
USER helixops

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default to API service
CMD ["python", "-m", "uvicorn", "helixops.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
