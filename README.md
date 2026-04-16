# AI020 Meeting Summarizer

AI020 turns Dutch government meeting PDFs into structured summaries, translated briefings, searchable speaker segments, and email digests.

## Stack

- Backend: FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite, uv
- AI: OpenAI SDK for structured chat/summarization when available, deterministic fallback when it is not
- Translation: LibreTranslate in Docker
- Email: Mailgun API when configured, otherwise HTML files in `emails/out/`
- Frontend: Vite, React 18, TypeScript, TailwindCSS, Zustand, TanStack Query, react-i18next, `@react-pdf-viewer/core`

## Repo Layout

```text
backend/     API, pipeline, models, services, scripts
brief/       Product brief and transcript fixtures
emails/      Jinja2 email templates and generated output
frontend/    Vite React frontend
infra/       Docker Compose stack
scripts/     Local helpers for warmup, mock inbound email, email build
tests/       Backend tests
```

## Environment

Copy the example file:

```bash
cp .env.example .env
```

Important variables:

```env
OPENAI_API_KEY=
LIBRETRANSLATE_URL=http://localhost:5000
LIBRETRANSLATE_API_KEY=
MAILGUN_API_KEY=
MAILGUN_DOMAIN=
INBOUND_EMAIL=
PUBLIC_BASE_URL=http://localhost:5173
ADMIN_EMAIL=admin@ai020.local
ADMIN_PASSWORD_HASH=
JWT_SECRET=
```

If `MAILGUN_API_KEY` is blank, digest emails are written to `emails/out/`.

## Backend

Install backend dependencies and run the API:

```bash
make dev
```

Useful endpoints:

- `GET /health`
- `GET /api/health`
- `GET /api/meetings`
- `GET /api/meetings/{id}`
- `GET /api/meetings/{id}/summary/{lang}`
- `GET /api/meetings/{id}/segments`
- `GET /api/meetings/{id}/speakers`
- `GET /api/meetings/{id}/pdf`
- `POST /api/meetings/{id}/chat`
- `POST /webhook/inbound`

All API errors use:

```json
{"error":{"code":"...","message":"...","detail":"..."}}
```

## LibreTranslate

Start the local services:

```bash
docker compose -f infra/docker-compose.yml up -d libretranslate mailhog
```

Then verify translation:

```bash
make translate-warmup
```

First-run note:

LibreTranslate downloads roughly 1 to 2 GB of Argos models on its first boot. During that period the container can stay in `health: starting` for 3 to 5 minutes. That is expected.

## Demo Flow

Seed demo subscribers:

```bash
make seed
```

Process the real 2021 Amsterdam PDF:

```bash
make process-sample
```

This writes the structured Dutch JSON to `backend/out/meeting-<id>.json` and stores translations in the database.

Run the offline inbound-email demo:

```bash
make mock-inbound
```

This posts a Mailgun-shaped multipart payload to `http://localhost:8000/webhook/inbound` and generates digest HTML in `emails/out/`.

## Email

Build inline-styled templates:

```bash
make build-emails
```

The build step tries to download the Amsterdam logo into `emails/assets/amsterdam-logo.png`.

## Frontend

Install dependencies:

```bash
make frontend-install
```

Run the app:

```bash
make dev-frontend
```

The frontend expects the backend at `http://localhost:8000` unless `VITE_API_BASE_URL` is set.

## Tests

Run backend tests:

```bash
make test
```

The suite covers health checks, translation cache behavior, real PDF extraction, sample transcript ingestion, and webhook-to-digest generation.

## Docker

Backend Dockerfile:

- `backend/Dockerfile`

Compose services:

- `backend`
- `libretranslate`
- `mailhog`
- optional Postgres block remains commented in `infra/docker-compose.yml`

## Deployment Notes

- Backend: Fly.io or any container host
- Frontend: Vercel or static hosting for Vite output
- LibreTranslate: host with enough disk for model downloads and persistent storage
- Mailgun: optional for real delivery; offline fallback is already built in
