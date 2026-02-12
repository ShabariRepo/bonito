#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Bonito API Integration Test Script
# Usage: ./scripts/test-api.sh [base_url] [email] [password]
# ─────────────────────────────────────────────────────────
set -eo pipefail

BASE="${1:-https://getbonito.com}"
# For API tests, hit Railway directly to avoid Vercel trailing-slash normalization
API_BASE="${API_BASE:-https://celebrated-contentment-production-0fc4.up.railway.app}"
EMAIL="${2:-shabari@bonito.ai}"
PASS="${3:-}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS_COUNT=0; FAIL_COUNT=0; SKIP_COUNT=0

# ── Helpers ──────────────────────────────────────────────

check() {
  local label="$1" method="$2" path="$3" status="$4"
  shift 4
  local resp
  resp=$(curl -s -o /tmp/bonito-test-body -w "%{http_code}" \
    -X "$method" "$API_BASE$path" \
    -H "Content-Type: application/json" \
    "$@" 2>/dev/null) || resp="000"
  
  local body
  body=$(cat /tmp/bonito-test-body 2>/dev/null || echo "")
  
  if [[ "$resp" == "$status" ]]; then
    echo -e "  ${GREEN}✓${NC} $label ${CYAN}($method $path → $resp)${NC}"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo -e "  ${RED}✗${NC} $label ${RED}($method $path → $resp, expected $status)${NC}"
    # Show error body if short
    if [[ ${#body} -lt 200 && -n "$body" ]]; then
      echo -e "    ${YELLOW}$body${NC}"
    fi
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
}

check_auth() {
  local label="$1" method="$2" path="$3" status="$4"
  shift 4
  check "$label" "$method" "$path" "$status" -H "Authorization: Bearer $TOKEN" "$@"
}

skip() {
  echo -e "  ${YELLOW}○${NC} $1 (skipped)"
  SKIP_COUNT=$((SKIP_COUNT+1))
}

section() {
  echo ""
  echo -e "${CYAN}━━━ $1 ━━━${NC}"
}

# ── 1. Health ────────────────────────────────────────────

section "Health Checks"
check "Basic health"     GET  /api/health      200
check "Liveness probe"   GET  /api/health/live  200
check "Readiness probe"  GET  /api/health/ready 200

# ── 2. Auth ──────────────────────────────────────────────

section "Authentication"

# Register a test account
TEST_EMAIL="test-$(date +%s)@bonito-test.dev"
TEST_PASS="TestPass123!"
check "Register new user" POST /api/auth/register 201 \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\",\"name\":\"API Test\"}"

# Login with provided creds (or test account if no password given)
if [[ -z "$PASS" ]]; then
  echo -e "  ${YELLOW}⚠ No password provided — using test account (unverified, login may 403)${NC}"
  LOGIN_EMAIL="$TEST_EMAIL"
  LOGIN_PASS="$TEST_PASS"
else
  LOGIN_EMAIL="$EMAIL"
  LOGIN_PASS="$PASS"
fi

LOGIN_RESP=$(curl -s -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$LOGIN_EMAIL\",\"password\":\"$LOGIN_PASS\"}" 2>/dev/null)

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [[ -n "$TOKEN" ]]; then
  echo -e "  ${GREEN}✓${NC} Login successful ${CYAN}(got access_token)${NC}"
  PASS_COUNT=$((PASS_COUNT+1))
else
  ERROR=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','') or d.get('detail',''))" 2>/dev/null || echo "unknown")
  echo -e "  ${RED}✗${NC} Login failed: ${YELLOW}$ERROR${NC}"
  FAIL_COUNT=$((FAIL_COUNT+1))
  
  # If login failed because email not verified, note it
  if [[ "$ERROR" == *"verify"* ]]; then
    echo -e "  ${YELLOW}  → Test user needs email verification. Pass a verified account: ./scripts/test-api.sh $BASE email password${NC}"
  fi
fi

if [[ -z "$TOKEN" ]]; then
  echo ""
  echo -e "${RED}Cannot continue without auth token. Provide credentials:${NC}"
  echo -e "  ./scripts/test-api.sh $BASE your@email.com yourpassword"
  echo ""
  echo -e "${CYAN}Results: ${GREEN}$PASS_COUNT passed${NC} · ${RED}$FAIL_COUNT failed${NC} · ${YELLOW}$SKIP_COUNT skipped${NC}"
  exit 1
fi

check_auth "Get current user"  GET /api/auth/me 200
check "Bad token rejected"     GET /api/auth/me 401 -H "Authorization: Bearer invalid-token"
check "Wrong credentials"      POST /api/auth/login 401 \
  -d '{"email":"nobody@test.com","password":"WrongPass1"}'

# ── 3. Providers ─────────────────────────────────────────

section "Providers"
check_auth "List providers"       GET  /api/providers/  200
PROVIDERS=$(curl -s "$API_BASE/api/providers/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
PROVIDER_COUNT=$(echo "$PROVIDERS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
echo -e "  ${CYAN}  → Found $PROVIDER_COUNT connected provider(s)${NC}"

if [[ "$PROVIDER_COUNT" -gt 0 ]]; then
  PROVIDER_ID=$(echo "$PROVIDERS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)
  check_auth "Get provider detail"  GET "/api/providers/$PROVIDER_ID" 200
  check_auth "Provider models"      GET "/api/providers/$PROVIDER_ID/models" 200
  check_auth "Provider costs"       GET "/api/providers/$PROVIDER_ID/costs" 200
else
  skip "Provider detail (no providers connected)"
  skip "Provider models (no providers connected)"
  skip "Provider costs (no providers connected)"
fi

# ── 4. Models ────────────────────────────────────────────

section "Models"
check_auth "List models"           GET /api/models/  200
MODELS=$(curl -s "$API_BASE/api/models/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
MODEL_COUNT=$(echo "$MODELS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else d.get('count',0))" 2>/dev/null || echo "0")
echo -e "  ${CYAN}  → Found $MODEL_COUNT model(s)${NC}"

if [[ "$MODEL_COUNT" -gt 0 ]]; then
  MODEL_ID=$(echo "$MODELS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if isinstance(d,list) else d['models'][0]['id'])" 2>/dev/null || echo "")
  if [[ -n "$MODEL_ID" ]]; then
    check_auth "Get model detail"  GET "/api/models/$MODEL_ID" 200
    check_auth "Model details (enriched)" GET "/api/models/$MODEL_ID/details" 200
  fi
fi

# ── 5. Dashboard / Analytics ─────────────────────────────

section "Dashboard & Analytics"
check_auth "Analytics overview"    GET /api/analytics/overview 200
check_auth "Usage stats"           GET /api/analytics/usage    200
check_auth "Trends"                GET /api/analytics/trends   200

# ── 6. Costs ─────────────────────────────────────────────

section "Costs"
check_auth "Cost overview"         GET /api/costs/   200
check_auth "Cost breakdown"        GET /api/costs/breakdown 200
check_auth "Cost forecast"         GET /api/costs/forecast  200
check_auth "Recommendations"       GET /api/costs/recommendations 200

# ── 7. Compliance ────────────────────────────────────────

section "Compliance"
check_auth "Compliance status"     GET /api/compliance/status   200
check_auth "Compliance checks"     GET /api/compliance/checks   200
check_auth "Frameworks"            GET /api/compliance/frameworks 200

# ── 8. Gateway ───────────────────────────────────────────

section "API Gateway"
check_auth "Gateway config"        GET /api/gateway/config 200
check_auth "Gateway keys"          GET /api/gateway/keys   200
check_auth "Gateway logs"          GET /api/gateway/logs   200
check_auth "Gateway usage"         GET /api/gateway/usage  200
skip "OpenAI-compat /v1/models (needs gateway API key, not JWT)"

# ── 9. Routing Policies ─────────────────────────────────

section "Routing Policies"
check_auth "List routing policies"  GET /api/routing-policies/ 200

# ── 10. Governance / Policies ────────────────────────────

section "Governance"
check_auth "List policies"         GET /api/policies/  200

# ── 11. Team / Users ─────────────────────────────────────

section "Team"
check_auth "List users"            GET /api/users/  200

# ── 12. Audit ────────────────────────────────────────────

section "Audit"
check_auth "Audit log"             GET /api/audit/  200

# ── 13. Notifications ────────────────────────────────────

section "Notifications"
check_auth "List notifications"    GET /api/notifications/      200
check_auth "Unread count"          GET /api/notifications/unread-count 200
check_auth "Preferences"           GET /api/notifications/preferences  200
check_auth "Alert rules"           GET /api/alert-rules/  200

# ── 14. Onboarding ──────────────────────────────────────

section "Onboarding"
check_auth "Onboarding progress"   GET /api/onboarding/progress  200

# ── 15. AI Copilot ──────────────────────────────────────

section "AI Copilot"
check_auth "Command bar"           POST /api/ai/command 200 \
  -d '{"query":"show costs"}'

# ── 16. Export ───────────────────────────────────────────

section "Export"
check_auth "Export formats"        GET /api/export/formats 200

# ── 17. Deployments ─────────────────────────────────────

section "Deployments"
check_auth "List deployments"      GET /api/deployments/ 200

# ── 18. Rate Limiting ───────────────────────────────────

section "Rate Limiting"
echo -e "  ${CYAN}  → Hitting login 12 times rapidly...${NC}"
RATE_LIMITED=false
for i in $(seq 1 12); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"ratelimit@test.com","password":"Test1234"}' 2>/dev/null)
  if [[ "$CODE" == "429" ]]; then
    RATE_LIMITED=true
    break
  fi
done
if $RATE_LIMITED; then
  echo -e "  ${GREEN}✓${NC} Rate limiter kicked in (429 after $i requests)"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo -e "  ${YELLOW}○${NC} Rate limiter not triggered in 12 requests (may have higher limit)"
  SKIP_COUNT=$((SKIP_COUNT+1))
fi

# ── Summary ──────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
echo -e "  ${GREEN}$PASS_COUNT passed${NC} · ${RED}$FAIL_COUNT failed${NC} · ${YELLOW}$SKIP_COUNT skipped${NC} · $TOTAL total"

if [[ $FAIL_COUNT -eq 0 ]]; then
  echo -e "  ${GREEN}🐟 All checks passed!${NC}"
else
  echo -e "  ${RED}⚠ $FAIL_COUNT endpoint(s) need attention${NC}"
fi
echo ""

# Cleanup
rm -f /tmp/bonito-test-body
exit $FAIL_COUNT
