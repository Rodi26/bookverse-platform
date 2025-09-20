#!/bin/bash

# Entrypoint script for BookVerse Platform Service
# Supports aggregator CLI mode

set -e

# Load authentication configuration if available
if [ -f "/app/config/auth.env" ]; then
    echo "Loading authentication configuration..."
    set -o allexport
    source /app/config/auth.env
    set +o allexport
fi

# Determine service mode
MODE="${1:-aggregator}"

case "$MODE" in
    "aggregator")
        echo "Starting Platform Aggregator CLI..."
        exec python -m app.main \
            --config /app/config/services.yaml \
            --output-dir /app/manifests \
            --source-stage PROD \
            "${@:2}"
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: $0 [aggregator] [additional-args...]"
        exit 1
        ;;
esac
