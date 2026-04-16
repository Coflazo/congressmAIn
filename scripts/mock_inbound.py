#!/usr/bin/env python3
"""Simulate a Mailgun inbound webhook POST for local testing without external services.

Usage:
    uv run python scripts/mock_inbound.py [--pdf PATH] [--url URL]

Defaults:
    pdf  = brief/real-transcript-20210527.pdf
    url  = http://localhost:8000/webhook/inbound
"""

import argparse
import sys
from pathlib import Path

import httpx

DEMO_SUBSCRIBERS = [
    ("demo-nl@ai020.local", "nl"),
    ("demo-en@ai020.local", "en"),
    ("demo-tr@ai020.local", "tr"),
    ("demo-pl@ai020.local", "pl"),
    ("demo-uk@ai020.local", "uk"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Mailgun inbound webhook")
    parser.add_argument("--pdf", default="brief/real-transcript-20210527.pdf")
    parser.add_argument("--url", default="http://localhost:8000/webhook/inbound")
    parser.add_argument("--api-base", default="http://localhost:8000")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Posting {pdf_path.name} to {args.url} ...")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    files = {
        "attachment-1": (pdf_path.name, pdf_bytes, "application/pdf"),
    }
    data = {
        "sender": "griffier@tweedekamer.nl",
        "recipient": "ai@sandbox-xxx.mailgun.org",
        "subject": f"Notulen plenaire vergadering — {pdf_path.stem}",
        "body-plain": "Beste, in de bijlage vindt u de notulen. Met vriendelijke groet.",
        "Message-Id": f"<mock-{pdf_path.stem}@mailgun.local>",
        "In-Reply-To": "",
    }

    try:
        for email, language in DEMO_SUBSCRIBERS:
            httpx.post(
                f"{args.api_base}/api/subscribers/",
                json={"email": email, "language": language, "topics": [], "frequency": "immediate"},
                timeout=30.0,
            )
        response = httpx.post(args.url, data=data, files=files, timeout=30.0)
        print(f"Status: {response.status_code}")
        print(response.text)
    except httpx.ConnectError:
        print(f"ERROR: Could not connect to {args.url}. Is the backend running?", file=sys.stderr)
        print("Run `make dev` first in another terminal.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
