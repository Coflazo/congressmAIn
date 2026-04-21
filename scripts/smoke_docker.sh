#!/usr/bin/env bash
# smoke_docker.sh — quick health check for the full docker compose stack
# Usage: bash scripts/smoke_docker.sh
# Expects: make up-full already ran (all services are up)

set -euo pipefail

COMPOSE_FILE="infra/docker-compose.yml"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
LT_URL="${LIBRETRANSLATE_URL:-http://localhost:5000}"
FALLBACK_URL="${FALLBACK_SERVER_URL:-http://localhost:4000}"
MAILHOG_URL="http://localhost:8025"
MAX_WAIT=120
INTERVAL=5

pass=0
fail=0

check() {
    local name="$1"
    local url="$2"
    local expected="${3:-}"

    if result=$(curl -sf "$url" 2>/dev/null); then
        if [ -n "$expected" ] && ! echo "$result" | grep -q "$expected"; then
            echo "  ✗ $name — responded but missing '$expected'"
            echo "    got: $(echo "$result" | head -c 120)"
            fail=$((fail + 1))
        else
            echo "  ✓ $name"
            pass=$((pass + 1))
        fi
    else
        echo "  ✗ $name — no response at $url"
        fail=$((fail + 1))
    fi
}

wait_for() {
    local name="$1"
    local url="$2"
    local elapsed=0
    echo "  Waiting for $name..."
    while ! curl -sf "$url" >/dev/null 2>&1; do
        if [ "$elapsed" -ge "$MAX_WAIT" ]; then
            echo "  ✗ $name timed out after ${MAX_WAIT}s"
            return 1
        fi
        sleep "$INTERVAL"
        elapsed=$((elapsed + INTERVAL))
    done
    echo "  ✓ $name is up (${elapsed}s)"
}

echo "── congressmAIn Docker smoke test ────────────────────────────"
echo "Compose file: $COMPOSE_FILE"
echo ""

# Wait for critical services
echo "Waiting for services to become ready..."
wait_for "backend" "${BACKEND_URL}/health"
wait_for "fallback-llm" "${FALLBACK_URL}/health"
# LibreTranslate takes longer on first boot (model downloads ~1-2GB)
wait_for "libretranslate" "${LT_URL}/languages" || true
echo ""

echo "Health checks:"
check "backend /health"          "${BACKEND_URL}/health"         '"status"'
check "backend /api/health"      "${BACKEND_URL}/api/health"     '"status"'
check "fallback-llm /health"     "${FALLBACK_URL}/health"        '"status"'
check "libretranslate /languages" "${LT_URL}/languages"          '"nl"'
check "mailhog web UI"           "${MAILHOG_URL}/api/v2/messages" '"total"'
echo ""

echo "API smoke checks:"
check "GET /api/meetings"        "${BACKEND_URL}/api/meetings"   '"meetings"'
echo ""

echo "Results: ${pass} passed, ${fail} failed"
if [ "$fail" -gt 0 ]; then
    echo ""
    echo "Tip: run 'docker compose -f ${COMPOSE_FILE} logs --tail=50' to diagnose failures."
    exit 1
fi

echo ""
echo "All services healthy."
