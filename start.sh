#!/bin/bash
# Production startup script for MultiSutra CMS

set -e

echo "Starting MultiSutra CMS..."

# Set default environment variables if not set
export FLASK_ENV=${FLASK_ENV:-production}
export DATABASE_URL=${DATABASE_URL:-sqlite:///multisutra.db}

echo "Environment: $FLASK_ENV"
echo "Database URL: $DATABASE_URL"

# Create necessary directories
mkdir -p static/uploads
mkdir -p instance
mkdir -p logs

echo "Starting Gunicorn server..."

# Start Gunicorn with production settings
exec gunicorn \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --worker-class sync \
    --timeout 120 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    run:app