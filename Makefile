.PHONY: dev test seed process-sample mock-inbound translate-warmup build-emails lint typecheck fallback-server up-full

# ── Fallback LLM server ────────────────────────────────────────────────────────
fallback-server:
	@echo "Starting free-tier LLM fallback server on http://localhost:4000..."
	uv run --with litellm --with fastapi --with "uvicorn[standard]" python scripts/fallback_server.py

# ── Docker (full stack including fallback LLM) ─────────────────────────────────
up-full:
	docker compose -f infra/docker-compose.yml up -d

# ── Local dev ──────────────────────────────────────────────────────────────────
dev:
	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Docker ─────────────────────────────────────────────────────────────────────
up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	cd backend && uv run pytest ../tests/ -v --tb=short

test-cov:
	cd backend && uv run pytest ../tests/ -v --tb=short --cov=. --cov-report=term-missing

# ── Seed / sample data ─────────────────────────────────────────────────────────
seed:
	cd backend && uv run python -m scripts.seed_demo

# ── Ingestion pipeline (real 2021 transcript) ──────────────────────────────────
process-sample:
	cd backend && uv run python -m scripts.process_meeting ../brief/real-transcript-20210527.pdf

# ── Mock inbound email (offline Mailgun simulation) ───────────────────────────
mock-inbound:
	uv run python scripts/mock_inbound.py

# ── LibreTranslate warmup ──────────────────────────────────────────────────────
translate-warmup:
	@echo "Waiting for LibreTranslate to be ready..."
	@bash scripts/translate_warmup.sh

# ── Email build (inline CSS) ───────────────────────────────────────────────────
build-emails:
	cd backend && uv run python ../scripts/build_emails.py

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

# ── Type checking / lint ───────────────────────────────────────────────────────
typecheck:
	cd backend && uv run mypy . --strict --ignore-missing-imports

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
