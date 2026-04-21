# Email setup

congressmAIn receives PDFs by email and sends digest briefings back to subscribers. The full flow works offline via `make mock-inbound`. Connecting a real email address takes about 10 minutes with a free Mailgun sandbox.

---

## Offline (no Mailgun account needed)

```bash
make mock-inbound
```

Posts a Mailgun-shaped multipart payload to `http://localhost:8000/webhook/inbound` using the sample PDF at `brief/real-transcript-20210527.pdf`. Digest HTML lands in `emails/out/`. No network access required.

---

## Mailgun sandbox (real inbound email, ~10 min setup)

A Mailgun sandbox gives you an address like `ai@sandbox-xxxxx.mailgun.org` instantly — no DNS setup, no domain ownership proof.

1. Create a free account at https://mailgun.com
2. Go to **Sending → Domains → your sandbox domain**
3. Under **Receiving**, create a route:
   - Filter: `match_recipient("ai@sandbox-xxxxx.mailgun.org")`
   - Action: `forward("https://your-backend.fly.dev/webhook/inbound")`
   - Priority: `10`
4. Set these in `.env`:
   ```env
   MAILGUN_API_KEY=key-xxxxx
   MAILGUN_DOMAIN=sandbox-xxxxx.mailgun.org
   INBOUND_EMAIL=ai@sandbox-xxxxx.mailgun.org
   ```
5. Restart the backend

To test: send an email with a PDF attachment to your sandbox address. The webhook fires, the pipeline runs, and subscribers receive digests.

---

## Outbound digests

| `MAILGUN_API_KEY` set? | Behavior |
|------------------------|----------|
| Yes | Sends via Mailgun API (real delivery) |
| No | Writes `emails/out/digest-{lang}.html` to disk |

Disk fallback is useful for local development — inspect the rendered email without a mail account.

---

## Product address

In UI copy and marketing materials, show `ai@gov.nl` as the product address. The actual receiving address always reads from `INBOUND_EMAIL` in `.env`. Never hardcode the email in source.

---

## Custom domain (optional)

To use a real subdomain:
1. Point MX records at Mailgun for your domain
2. Verify domain ownership in Mailgun dashboard
3. Update `MAILGUN_DOMAIN` and `INBOUND_EMAIL`

DNS propagation typically takes 20–40 minutes.
