#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "═══════════════════════════════════════"
echo "  Bonito Test Suite"
echo "═══════════════════════════════════════"

echo ""
echo "▶ Running backend tests..."
bash scripts/test-backend.sh

echo ""
echo "▶ Running frontend E2E tests..."
bash scripts/test-frontend.sh

echo ""
echo "✅ All tests complete."
