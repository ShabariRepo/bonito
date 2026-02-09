#!/bin/sh
# Production startup script for backend
# Runs migrations then starts the server
set -e

echo "🐟 Bonito Backend — Production Start"

# Run database migrations
echo "⏳ Running Alembic migrations..."
python -m alembic upgrade head
echo "✅ Migrations complete."

# Start the server
echo "🚀 Starting uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-4}" \
    --log-level info
