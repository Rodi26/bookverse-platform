# BookVerse Core Demo Application Dockerfile
#
# DEMO PURPOSE: This Dockerfile demonstrates how services using bookverse-core
# can be containerized with consistent patterns and configurations.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for demo
ENV PYTHONPATH=/app
ENV DEMO_ENVIRONMENT=production
ENV DEMO_LOG_LEVEL=INFO
ENV DEMO_AUTH_ENABLED=true
ENV DEMO_DEVELOPMENT_MODE=false

# Install system dependencies (minimal for demo)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bookverse-core library
COPY bookverse_core/ ./bookverse_core/
COPY pyproject.toml .

# Install the library in the container
RUN pip install -e .

# Copy demo application
COPY app/ ./app/
COPY config/ ./config/

# Create directory for SQLite database
RUN mkdir -p /app/data

# Set database path for containerized environment
ENV DEMO_DATABASE_URL=sqlite:///./data/demo.db

# Expose the demo application port
EXPOSE 8000

# Health check using the standardized health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash demo && \
    chown -R demo:demo /app
USER demo

# Command to run the demo application
CMD ["python", "app/main.py"]

# Alternative commands for different scenarios:
# Development with reload: CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# Production with gunicorn: CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# Demo labels for container metadata
LABEL maintainer="BookVerse Team <team@bookverse.com>"
LABEL description="BookVerse Core Library Demo Application"
LABEL version="0.1.0"
LABEL demo.purpose="Demonstrate bookverse-core library eliminating code duplication"
LABEL demo.eliminates="1124 lines of authentication duplication + configuration standardization"
