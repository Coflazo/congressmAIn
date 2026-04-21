# congressmAIn — Claude Code project brief

Dutch government meeting PDFs → multilingual plain-language summaries, delivered by email and a React web platform.

## Repo layout

```
backend/        FastAPI app — routes, pipeline, models, services
  pipeline/     ingest.py (PDF → segments → summary → translations)
  services/     openai_client.py (httpx fallback LLM), translate.py (LibreTranslate)
brief/          Sample PDFs and pipeline fixtures
design/         UI mockups (Stitch HTML — visual source of truth for the frontend)
docs/           Guides — email-setup, e2e-testing, stitch-prompt
emails/         Jinja2 digest templates
frontend/       Vite + React 18 + TypeScript + Tailwind
infra/          Docker Compose (backend, fallback-llm, libretranslate, mailhog)
scripts/        fallback_server.py, mock_inbound.py, smoke_docker.sh, translate_warmup.sh
skills/         LLM prompt assets and output-schema.json
tests/          pytest suite (30 tests)
```

## LLM setup

No OpenAI or Anthropic key needed. All LLM calls go to a local LiteLLM Router proxy:

```
scripts/fallback_server.py  →  http://localhost:4000
```

Proxy chains 12 free-tier providers. Keys live in `/Users/pc/Desktop/api_keys.txt` (not committed). Start with `make fallback-server`.

Config vars: `FALLBACK_SERVER_URL=http://localhost:4000`, `FALLBACK_MODEL=t0-deepseek`.

## Key services

| Service | Default port | Start |
|---------|-------------|-------|
| FastAPI backend | :8000 | `make dev` |
| Vite frontend | :5173 | `make dev-frontend` |
| Fallback LLM proxy | :4000 | `make fallback-server` |
| LibreTranslate | :5000 | `make up-full` |
| Mailhog | :8025 | `make up-full` |

## Make targets

```
make dev              # FastAPI hot-reload
make dev-frontend     # Vite dev server
make fallback-server  # LLM proxy (uv-based, no Docker)
make up-full          # Docker: all services
make test             # pytest
make seed             # bootstrap admin + demo subscribers
make process-sample   # run brief/real-transcript-20210527.pdf through full pipeline
make mock-inbound     # simulate inbound email (offline)
make translate-warmup # verify LibreTranslate has nl/en/tr/pl/uk
make smoke-test       # Docker health checks for all services
make build-emails     # inline CSS into Jinja2 templates
```

## Design tokens

All colors and spacing live in `frontend/src/styles/tokens.css`, mirrored in `tailwind.config.js`. Never hardcode colors — always `var(--token-name)` or the Tailwind class. Core palette: `--color-primary: #831517` (Amsterdam red), `--color-background: #fcf9f2` (warm paper).

## Comment style

Comments should read like a developer who just figured something out — direct and specific about why, not what.

## E2E checks

See `docs/e2e-testing.md`. Three checks: `make mock-inbound`, `make smoke-test`, `make translate-warmup`.
