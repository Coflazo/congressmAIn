# congressmAIn

Dutch local government publishes hundreds of meeting minutes every month. Most residents never read them. congressmAIn changes that: forward a PDF to an email address, get back a plain-language summary in your language.

The pipeline runs on free-tier LLMs (no paid API account required), translates to Dutch, English, Turkish, Polish, and Ukrainian via LibreTranslate, and serves a web app where you can browse speaker quotes, read decisions with voting records, and ask follow-up questions grounded in the transcript.

## How it works

1. A PDF lands at `ai@gov.nl` (or whatever `INBOUND_EMAIL` you configure)
2. The pipeline extracts text and identifies who said what
3. A structured Dutch summary is generated, then translated to five languages
4. Subscribers get a digest email with key decisions and a link to the platform
5. On the platform: PDF with speaker highlights, decision timeline, and an AI chat that cites specific passages

## Stack

- Backend — FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite (Postgres-compatible), uv
- AI — LiteLLM Router proxying 12 free providers (DeepSeek, Groq, Mistral, Gemini, Cerebras, and more) at localhost:4000
- Translation — LibreTranslate (nl/en/tr/pl/uk, self-hosted in Docker)
- Email — Mailgun for real delivery; writes to disk when key is unset
- Frontend — Vite, React 18, TypeScript, Tailwind, Zustand, TanStack Query, `@react-pdf-viewer/core`

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/Coflazo/congressmAIn.git
cd congressmAIn
cp .env.example .env
```

Set at minimum `JWT_SECRET` and `ADMIN_PASSWORD_HASH` in `.env`. Everything else defaults to local development values.

### 2. LLM keys

congressmAIn doesn't need an OpenAI or Anthropic account. Copy the key template and fill in at least one free-tier key:

```bash
cp api_keys.txt.example api_keys.txt
# edit api_keys.txt
```

Free accounts worth having: [DeepSeek](https://platform.deepseek.com) · [Groq](https://console.groq.com) · [Mistral](https://console.mistral.ai) · [Gemini](https://aistudio.google.com)

### 3. Start services

```bash
make up-full           # Docker: backend, LibreTranslate, Mailhog, fallback LLM
make translate-warmup  # wait for LibreTranslate models (~1–2 GB, first boot only)
```

Or run components individually without Docker:

```bash
make fallback-server   # LLM proxy on :4000
make dev               # FastAPI on :8000
make dev-frontend      # Vite on :5173
```

### 4. Try it

```bash
make seed           # create admin user and demo subscribers
make process-sample # run a real 2021 Amsterdam PDF through the full pipeline
make mock-inbound   # simulate an inbound email with that PDF
```

Then open http://localhost:5173.

## Repo layout

```
backend/     FastAPI app — routes, pipeline, models, services
brief/       Sample PDFs and pipeline fixtures
design/      UI mockups (Stitch HTML files, visual source of truth)
docs/        Guides — email setup, E2E testing, design prompt
emails/      Jinja2 digest templates and generated output
frontend/    React + Vite app
infra/       Docker Compose stack
scripts/     Helpers — fallback LLM server, mock inbound, warmup, smoke tests
skills/      LLM prompt assets and structured output schema
tests/       Backend test suite
```

## Environment variables

```env
# LLM fallback
FALLBACK_SERVER_URL=http://localhost:4000
FALLBACK_MODEL=t0-deepseek

# Translation
LIBRETRANSLATE_URL=http://localhost:5000
LIBRETRANSLATE_API_KEY=

# Email
MAILGUN_API_KEY=
MAILGUN_DOMAIN=
INBOUND_EMAIL=

# App
PUBLIC_BASE_URL=http://localhost:5173
ADMIN_EMAIL=admin@congressmain.local
ADMIN_PASSWORD_HASH=
JWT_SECRET=
```

When `MAILGUN_API_KEY` is not set, digest emails write to `emails/out/` instead of sending. Everything else keeps working.

## API

```
GET  /health
GET  /api/meetings
GET  /api/meetings/{id}
GET  /api/meetings/{id}/summary/{lang}
GET  /api/meetings/{id}/segments
GET  /api/meetings/{id}/speakers
GET  /api/meetings/{id}/pdf
POST /api/meetings/{id}/chat
POST /webhook/inbound
```

Errors always return `{"error": {"code": "...", "message": "...", "detail": "..."}}`.

## Tests

```bash
make test       # full suite
make test-cov   # with coverage report
```

30 tests covering health endpoints, translation caching, PDF extraction, pipeline ingestion, and the full webhook-to-digest flow.

## End-to-end checks

See `docs/e2e-testing.md` for the three manual smoke tests: mock inbound email, Docker stack, and LibreTranslate warmup.

```bash
# Terminal 1 — backend running
make dev

# Terminal 2 — E2E checks
make mock-inbound
make up-full && bash scripts/smoke_docker.sh
make translate-warmup
```

## Email setup

`docs/email-setup.md` covers Mailgun sandbox setup (about 10 minutes, no DNS required) and connecting a custom domain.

Short version: `make mock-inbound` works fully offline. For real email, create a free Mailgun sandbox and point a receiving route at `/webhook/inbound`.

## LibreTranslate

On first boot, LibreTranslate downloads Argos translation models for nl, en, tr, pl, and uk — roughly 1–2 GB total. The container sits in `health: starting` for 3–5 minutes while this happens. That's expected. Run `make translate-warmup` once to confirm all languages loaded correctly.

## Docker

```bash
make up-full    # start all services
make down       # stop
```

Services: `backend`, `fallback-llm`, `libretranslate`, `mailhog`. Optional Postgres block is commented out in `infra/docker-compose.yml` if you want to swap away from SQLite.

## Deploy

- Backend: Fly.io or any container host
- Frontend: Vercel or any static host (`make frontend-build` produces `frontend/dist/`)
- LibreTranslate: needs a persistent volume with ~3 GB for model storage
- Mailgun: optional — disk fallback works fine without it

## Design

Mockups live in `design/`. Each subfolder is a standalone HTML file from Google Stitch. The React frontend in `frontend/` is a direct conversion with the same design tokens.

To regenerate or iterate on a screen, use the prompt in `docs/stitch-prompt.md`.
