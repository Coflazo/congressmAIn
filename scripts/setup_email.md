# Email Setup

## Path taken

**Local mock first** — used for the core hackathon demo path.

The product works fully offline through `make mock-inbound`, which posts a Mailgun-shaped request to the webhook and writes digest HTML to `emails/out/`.

**Mailgun sandbox** remains the quickest real inbound path when you want to connect the project to a live email address.

Mailgun sandbox addresses (`ai@sandbox-XXX.mailgun.org`) require no DNS setup and work
instantly. The address is configured via the `INBOUND_EMAIL` env var.

## Inbound (receiving PDFs)

1. Create a free Mailgun account at https://mailgun.com
2. Go to Sending → Domains → your sandbox domain
3. Under Routes, create a route:
   - Filter: `match_recipient("ai@sandbox-XXX.mailgun.org")`
   - Action: `forward("https://your-backend.fly.dev/webhook/inbound")`
4. Set `INBOUND_EMAIL=ai@sandbox-XXX.mailgun.org` in `.env`

For local testing, skip Mailgun entirely:

```bash
make mock-inbound
```

This posts `brief/real-transcript-20210527.pdf` directly to `http://localhost:8000/webhook/inbound`.

## Outbound (sending digests)

- If `MAILGUN_API_KEY` is set: sends via Mailgun API
- If not set: writes HTML to `emails/out/*.html` for inspection

## Pitch-deck address

In UI copy, display `ai@gov.nl` as the product address (aspirational).
The real functional address reads from `INBOUND_EMAIL` env var — never hardcode it.

## FreeDomain alternative

If you want a real subdomain (not sandbox), open an issue at
https://github.com/DigitalPlatDev/FreeDomain requesting a subdomain like
`ai020.gov.nl`, point MX records at Mailgun, then update `INBOUND_EMAIL`.
This is a 20+ minute process; use sandbox for hackathon demos.
