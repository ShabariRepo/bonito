#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway"

echo "Starting application..."
exec "$@"
