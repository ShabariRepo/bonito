#!/bin/sh
# Production startup script for backend
set -e

echo "🐟 Bonito Backend — Production Start"
echo "PORT=${PORT:-8000}"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'NO!')"
echo "REDIS_URL set: $([ -n "$REDIS_URL" ] && echo 'yes' || echo 'NO!')"

# Run database migrations
echo "⏳ Running Alembic migrations..."
if python -m alembic upgrade head 2>&1; then
    echo "✅ Migrations complete."
else
    echo "❌ Migration FAILED — check alembic history. Continuing startup but DB may be out of sync."
    # Don't exit — the app can still serve health checks and help diagnose.
    # But log loudly so it shows up in Railway logs.
fi

# Start the server
echo "🚀 Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-2}" \
    --log-level info
