#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"

echo "▶ Frontend E2E tests (Playwright)"

if ! npx playwright --version &>/dev/null 2>&1; then
    echo "  Installing Playwright..."
    npm install -D @playwright/test
    npx playwright install --with-deps chromium
fi

npx playwright test "$@"
