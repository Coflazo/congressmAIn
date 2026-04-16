# PROGRESS — AI020 Meeting Summarizer

## Phase 1: Backend Scaffold — DONE ✓ (24/24 tests green)

**Goal**: Working FastAPI backend with DB, OpenAI wrapper, LibreTranslate wrapper, and Docker stack. No pipeline logic yet — just infrastructure that all later phases build on.

### Files to create

```
/backend
  pyproject.toml          — uv project file, all deps
  main.py                 — FastAPI app + router mounts
  database.py             — SQLAlchemy engine + session + Base
  models.py               — Meeting, Segment, Translation, Subscriber, ChatMessage ORM models
  taxonomy.py             — fixed topic taxonomy list
  schemas/
    meeting.py            — Pydantic v2 request/response models (matches output-schema.json)
  services/
    openai_client.py      — OpenAI wrapper (60s timeout, 2 retries, JSON logging, cost tracking)
    translate.py          — LibreTranslate wrapper (120s timeout, 3 retries, SHA256 cache in DB)
  routers/
    meetings.py           — GET /api/meetings, GET /api/meetings/{id}
    webhook.py            — POST /webhook/inbound (stub — wired in Phase 5)
    chat.py               — POST /api/meetings/{id}/chat (stub)
    admin.py              — admin routes (stub)
    subscribers.py        — subscriber CRUD (stub)
  logs/                   — gitignored, created at runtime
    openai.log
    translate.log

/infra
  docker-compose.yml      — libretranslate, mailhog, optional postgres

/scripts
  mock_inbound.py         — POST Mailgun-shaped payload for offline testing
  build_emails.py         — inline CSS step (stub)
  setup_email.md          — documents email setup path taken
  translate_warmup.sh     — boot check + smoke translation nl→en

/emails
  digest.html.j2          — Jinja2 template (stub)
  assets/                 — amsterdam-logo.png (downloaded at build)
  out/                    — gitignored, generated digests land here

/tests
  conftest.py
  test_translate.py       — smoke tests for LibreTranslate wrapper
  test_openai_client.py   — mock-based tests for retry/logging

/frontend                 — empty; scaffolded in Phase 6

.env.example
Makefile
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| SQLite default, Postgres-compatible schema | Zero setup for local; swap connection string for prod |
| SHA256(text+source+target) translation cache in DB | Avoid re-translating same text on reprocess |
| asyncio.gather + semaphore=3 for translation fan-out | Don't hammer local LibreTranslate container |
| gpt-4o-mini for structural tasks (segmenter, classifier) | Cost — these run on every chunk |
| gpt-4o for plain-language summarizer | Quality — one call per meeting |
| Structured outputs (`response_format=json_schema`) for all LLM calls | Never parse free text |
| Fall back to `emails/out/*.html` if MAILGUN_API_KEY unset | Local dev without Mailgun |

### Phase 1 completion criteria
- [ ] `make dev` starts FastAPI on :8000 with hot reload
- [ ] `GET /health` returns `{"status":"ok","libretranslate":"reachable"}`
- [ ] `docker compose up` brings up LibreTranslate + Mailhog
- [ ] `make translate-warmup` exits 0 (all 5 languages present, nl→en smoke works)
- [ ] `pytest tests/` green

---

## Phase 2: edgeparse + Ingestion Pipeline — PENDING

Steps: edgeparse PDF extraction → speaker segmenter (gpt-4o-mini) → topic classifier (gpt-4o-mini) → Dutch summarizer (gpt-4o) → translation fan-out. Validate with `make process-sample`.

## Phase 3: Inbound Webhook + Email — PENDING

POST /webhook/inbound parses Mailgun payload. Outbound digest via Mailgun or disk fallback. `make mock-inbound` must produce HTML in emails/out/.

## Phase 4: Email setup — PENDING (timebox 20 min, fall back to Mailgun sandbox)

## Phase 5: Frontend scaffold — PENDING

Vite + React 18 + TS + Tailwind + shadcn/ui. Convert stitch/ HTML to components. Design tokens from stitch/ tailwind config into tokens.css.

## Phase 6: PDF viewer + speaker highlight — PENDING

@react-pdf-viewer/core + custom bbox highlight plugin. Zustand store for activeSpeaker.

## Phase 7: Chat (RAG) — PENDING

TF-IDF retrieval, top-8 segments, structured output with citations, cross-language flow.

## Phase 8: Admin panel + metrics — PENDING

JWT auth, admin seed from env. Meetings table + subscribers table + metrics dashboard.

## Phase 9: Dockerize + deploy docs — PENDING

Dockerfile for backend. Fly.io + Vercel deployment instructions in README.md.

---

## Design tokens (from stitch/)

Extracted from all stitch HTML files — canonical source of truth for frontend.

```
primary:           #831517
primary-container: #a42e2b
on-primary:        #ffffff
secondary:         #665e3c
secondary-container: #ece0b4
tertiary:          #194b30
background:        #fcf9f2
surface:           #fcf9f2
surface-container-low: #f6f3ec
surface-container: #f1eee7
surface-container-high: #ebe8e1
surface-container-highest: #e5e2db
surface-container-lowest: #ffffff
on-surface:        #1c1c18
on-surface-variant: #58413f
outline-variant:   #dfbfbc
error:             #ba1a1a

border-radius DEFAULT: 0.125rem (2px) — very sharp
border-radius lg:      0.25rem (4px)
border-radius xl:      0.5rem (8px)

fonts:
  headline/serif: Newsreader
  body/label:     Inter
  mono:           JetBrains Mono
```

---

## Open questions (none blocking phase 1)

1. **edgeparse**: Not on PyPI as of knowledge cutoff. Plan: `pip install git+https://github.com/raphaelmansuy/edgeparse.git`. If the repo doesn't expose a clean `parse_pdf()` API, fall back to `pypdf` + `pdfplumber` for text extraction and note the substitution.
2. **INBOUND_EMAIL**: Will use Mailgun sandbox for local testing. Email path documented in scripts/setup_email.md.
3. **poppler-utils**: Required to render the real PDF for testing (`brief/real-transcript-20210527.pdf`). Added to docker-compose backend service. Local testers need `brew install poppler`.
