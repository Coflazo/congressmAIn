#!/usr/bin/env bash
# translate_warmup.sh — verify LibreTranslate is up and has all required languages
# Usage: bash scripts/translate_warmup.sh

set -euo pipefail

LT_URL="${LIBRETRANSLATE_URL:-http://localhost:5000}"
REQUIRED_LANGS=("nl" "en" "tr" "pl" "uk")
MAX_WAIT=300  # 5 minutes
INTERVAL=10

echo "── LibreTranslate warmup ──────────────────────────────────────"
echo "Endpoint: $LT_URL"
echo "Waiting up to ${MAX_WAIT}s for models to load..."
echo ""

elapsed=0
while true; do
    if curl -sf "${LT_URL}/languages" -o /tmp/lt_langs.json 2>/dev/null; then
        echo "✓ LibreTranslate responded"
        break
    fi
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "ERROR: LibreTranslate did not respond within ${MAX_WAIT}s"
        echo "Tip: run 'docker compose -f infra/docker-compose.yml up -d libretranslate'"
        exit 1
    fi
    echo "  Waiting... (${elapsed}s elapsed)"
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done

# Check required languages
echo ""
echo "Checking language availability..."
missing=()
for lang in "${REQUIRED_LANGS[@]}"; do
    if python3 -c "
import json, sys
langs = json.load(open('/tmp/lt_langs.json'))
codes = {l['code'] for l in langs}
sys.exit(0 if '${lang}' in codes else 1)
" 2>/dev/null; then
        echo "  ✓ ${lang}"
    else
        echo "  ✗ ${lang} MISSING"
        missing+=("$lang")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo "ERROR: Missing languages: ${missing[*]}"
    echo "Check LT_LOAD_ONLY env var in infra/docker-compose.yml"
    exit 1
fi

# Smoke translation: nl → en
echo ""
echo "Smoke translation nl→en..."
RESULT=$(curl -sf "${LT_URL}/translate" \
    -H "Content-Type: application/json" \
    -d '{"q":"De gemeenteraad vergadert vandaag","source":"nl","target":"en","format":"text"}' \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['translatedText'])")

if [ -n "$RESULT" ]; then
    echo "  Input:  De gemeenteraad vergadert vandaag"
    echo "  Output: $RESULT"
    echo ""
    echo "✓ LibreTranslate warmup complete — all ${#REQUIRED_LANGS[@]} languages ready"
else
    echo "ERROR: Smoke translation returned empty result"
    exit 1
fi
