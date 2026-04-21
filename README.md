<div align="center">

# congressmAIn

**Dutch council meetings, made readable for everyone**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

*Built at the AISO × AI020 Gov Tech Hackathon · Apr 2026 · Invited to demo with Amsterdam Municipality*

</div>

---

Dutch local government publishes hundreds of meeting minutes every month. Most residents never read them. congressmAIn changes that: forward a PDF to an email address, get back a plain-language summary in your language — with decisions, vote records, and what each outcome means for your neighbourhood.

The pipeline runs entirely on **free-tier LLMs** (no OpenAI account required), translates to five languages, and serves a web platform where you can read speaker quotes in context, browse decisions, and ask follow-up questions grounded in the transcript.

---

## How it works

```
PDF email arrives
       │
       ▼
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Text extraction │────▶│  Speaker diarisation  │────▶│  Agenda parsing  │
│  (pdfplumber +   │     │  (regex + heuristics) │     │  (rule-based +   │
│   pypdf)         │     └──────────────────────┘     │   LLM refinement)│
└─────────────────┘                                   └────────┬─────────┘
                                                               │
                    ┌──────────────────────────────────────────┘
                    ▼
          ┌──────────────────┐     ┌───────────────────┐
          │  LiteLLM Router  │────▶│  LibreTranslate   │
          │  12 free models  │     │  nl/en/tr/pl/uk   │
          └──────────────────┘     └────────┬──────────┘
                                            │
                    ┌───────────────────────┘
                    ▼
       ┌────────────────────┐       ┌──────────────────┐
       │  Digest email sent  │       │  Web platform    │
       │  (per subscriber    │       │  PDF highlights  │
       │   language + topic) │       │  AI chat + votes │
       └────────────────────┘       └──────────────────┘
```

---

## Features

| | |
|---|---|
| **Zero-cost AI** | Routes across 12 free LLM providers — DeepSeek, Groq, Mistral, Gemini, Cerebras, and more. Falls back automatically if any provider is down. |
| **5 languages** | Summaries in Dutch, English, Turkish, Polish, and Ukrainian via self-hosted LibreTranslate. |
| **PDF with speaker highlights** | Select a speaker and their passages glow in the original document. |
| **Batched LLM pipeline** | Each agenda item gets its own B1-Dutch summary without hitting token limits. |
| **Email delivery** | Subscribers filter by topic and language. Works fully offline (writes to disk) without Mailgun. |
| **Hamerstuk detection** | Items passed without debate are automatically marked as uncontested. |

---

## Stack

```
Backend       FastAPI · SQLAlchemy 2.x · Pydantic v2 · SQLite · uv
AI            LiteLLM Router → 12 free providers
Translation   LibreTranslate (Docker, self-hosted)
Email         Mailgun / disk fallback
Frontend      Vite · React 18 · TypeScript · Tailwind · Zustand · TanStack Query
PDF           @react-pdf-viewer/core with custom bbox overlay renderer
```

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/Coflazo/congressmAIn.git
cd congressmAIn
cp .env.example .env          # set JWT_SECRET and ADMIN_PASSWORD_HASH
```

### 2. LLM keys (free accounts only)

```bash
cp api_keys.txt.example api_keys.txt
# fill in at least one: DeepSeek · Groq · Mistral · Gemini
```

### 3. Start

**With Docker (recommended for full stack):**
```bash
make up-full           # backend + LibreTranslate + Mailhog + LLM proxy
make translate-warmup  # wait for Argos models (~1–2 GB, first boot only)
```

**Without Docker (faster for development):**
```bash
# Terminal 1 — LLM proxy
make fallback-server

# Terminal 2 — FastAPI backend
make dev

# Terminal 3 — React frontend
make dev-frontend
```

### 4. Try it

```bash
make seed            # create admin user + demo subscribers
make process-sample  # run a real 2021 Amsterdam council PDF
```

Open **http://localhost:5173** — the processed meeting will appear in the list.

---

## Environment variables

```env
# LLM
FALLBACK_SERVER_URL=http://localhost:4000
FALLBACK_MODEL=t0-deepseek

# Translation
LIBRETRANSLATE_URL=http://localhost:5000

# Email (optional — omit to use disk fallback)
MAILGUN_API_KEY=
MAILGUN_DOMAIN=
INBOUND_EMAIL=

# App
PUBLIC_BASE_URL=http://localhost:5173
ADMIN_EMAIL=admin@congressmain.local
ADMIN_PASSWORD_HASH=
JWT_SECRET=
```

---

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

---

## Repo layout

```
backend/     FastAPI app — routes, pipeline, models, services
brief/       Sample PDFs and fixtures
design/      UI mockups (Stitch HTML — visual source of truth)
docs/        Email setup, E2E testing, design prompt
emails/      Jinja2 digest templates + generated output
frontend/    React + Vite app
infra/       Docker Compose stack
scripts/     LLM proxy, mock inbound, warmup, smoke tests
skills/      LLM prompts and output schema
tests/       30-test backend suite
```

---

## Tests

```bash
make test      # full suite (30 tests)
make test-cov  # with coverage report
```

---

## Notes

**LibreTranslate first boot:** downloads ~1–2 GB of Argos language models. The container stays `health: starting` for 3–5 minutes. That's expected — run `make translate-warmup` once to confirm all languages loaded.

**Mailgun:** optional. Without a key, digest emails write to `emails/out/` instead of sending. Every other feature works normally.

---

<div align="center">

Made in Amsterdam · AISO × AI020 Gov Tech Hackathon · Apr 2026

</div>
