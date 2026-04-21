# End-to-end testing

Three manual E2E checks cover the full stack. Run them in order — each one depends on the previous.

---

## 1. Mock inbound email

Simulates a council clerk forwarding a PDF to `ai@gov.nl`. No Mailgun account needed.

**Requires:** backend running (`make dev` in another terminal).

```bash
make mock-inbound
```

What happens:
- Reads `brief/real-transcript-20210527.pdf`
- Posts a Mailgun-shaped multipart request to `http://localhost:8000/webhook/inbound`
- Backend runs the full pipeline: PDF extraction → speaker segmentation → summarization → translation fan-out
- Writes digest HTML to `emails/out/` (one file per subscriber language)

Pass criteria:
- No 4xx/5xx response from the webhook
- `emails/out/` contains at least one `digest-*.html` file
- Each HTML file has a non-empty meeting title and summary section

---

## 2. Docker full-stack smoke test

Spins up all four services and verifies every health endpoint responds correctly.

**Requires:** Docker Desktop running.

```bash
make up-full
bash scripts/smoke_docker.sh
```

What it checks:
| Service | Endpoint | Expected |
|---------|----------|----------|
| backend | `/health` | `{"status":"ok"}` |
| backend | `/api/health` | status ok |
| fallback-llm | `/health` | `{"status":"ok"}` |
| libretranslate | `/languages` | contains `"nl"` |
| mailhog | `/api/v2/messages` | JSON with `"total"` key |
| backend | `/api/meetings` | JSON with `"meetings"` key |

First-boot note: LibreTranslate downloads ~1–2 GB of Argos translation models on initial start. The container stays in `health: starting` for 3–5 minutes. `smoke_docker.sh` waits up to 2 minutes before failing. Run `make translate-warmup` separately after models finish downloading.

---

## 3. LibreTranslate warmup

Verifies all five required languages loaded and runs a smoke translation.

```bash
make translate-warmup
```

Checks:
- `nl`, `en`, `tr`, `pl`, `uk` all present in `/languages` response
- Translates "De gemeenteraad vergadert vandaag" nl→en and prints the result

Pass criteria:
- All five language codes present
- Smoke translation returns a non-empty English string

If languages are missing, check `LT_LOAD_ONLY` in `infra/docker-compose.yml` — it must include all five codes.

---

## Running all three

```bash
# Terminal 1: start backend
make dev

# Terminal 2: run E2E checks
make mock-inbound
make up-full && bash scripts/smoke_docker.sh
make translate-warmup
```

All three pass = the product is working end-to-end.
