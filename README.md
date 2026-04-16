# AI020 Meeting Summarizer

Municipal Meeting Summarizer turns Dutch government meeting PDFs into structured, plain-language summaries for residents. The current stack is FastAPI + SQLite on the backend, LibreTranslate for multilingual output, and a frontend that will be added in later phases.

## Repo Structure

```text
backend/        FastAPI app, database models, routers, services
brief/          Product brief, sample transcript, expected output
infra/          Docker Compose for local services
scripts/        Warmup, mock inbound email, email build helpers
skills/         Dutch gov context, plain-language rules, output schema
tests/          Backend test suite
stitch/         Design source files for the frontend phase
```

## Environment

Copy `.env.example` to `.env` and fill in the values you have:

```bash
cp .env.example .env
```

Required for the current backend work:

- `OPENAI_API_KEY`
- `LIBRETRANSLATE_URL`
- `PUBLIC_BASE_URL`
- `JWT_SECRET`

Mailgun values can stay blank for local development until the email phase.

## Local Development

Install backend dependencies with `uv`, then start the API:

```bash
make dev
```

The backend health endpoints are:

- `GET /health`
- `GET /api/health`

Both return `200` when LibreTranslate is reachable and `503` when it is not.

## LibreTranslate Setup

Start LibreTranslate locally with Docker Compose:

```bash
docker compose -f infra/docker-compose.yml up -d libretranslate
```

Then run the warmup check:

```bash
make translate-warmup
```

What the warmup does:

- waits for `LIBRETRANSLATE_URL/languages`
- verifies `nl`, `en`, `tr`, `pl`, and `uk`
- runs a smoke translation from Dutch to English

First-run note:

LibreTranslate downloads roughly 1 to 2 GB of language models the first time it boots. During that initial load, the container can look unhealthy for 3 to 5 minutes. That is expected; wait for the models to finish loading, then rerun `make translate-warmup`.

## Testing

Run the backend tests with:

```bash
make test
```

The IDE may show import warnings if it is pointing at the system Python instead of the `uv` virtual environment. The test command uses the project environment under `backend/.venv`.
