#!/bin/bash
set -e

# Fix ownership on Railway persistent volume (mounted as root)
if [ -d "/data/memwright" ]; then
    chown -R app:app /data/memwright
fi

echo "Running database migrations..."
gosu app alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway"

echo "Starting application..."
exec gosu app "$@"
