#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ Backend tests (pytest)"

if command -v docker &>/dev/null && docker compose ps --services 2>/dev/null | grep -q backend; then
    echo "  Running inside Docker..."
    docker compose exec backend pytest -v --tb=short
else
    echo "  Running locally..."
    cd backend
    python -m pytest -v --tb=short
fi
