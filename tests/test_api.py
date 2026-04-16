"""Integration tests for FastAPI endpoints — in-memory DB, no external services."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def test_health_endpoint(client):
    """GET /health returns 200 or 503 (depends on LibreTranslate availability)."""
    response = client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "libretranslate" in data


def test_api_health_endpoint(client):
    """GET /api/health mirrors the main health payload."""
    response = client.get("/api/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "libretranslate" in data


def test_list_meetings_empty(client):
    """GET /api/meetings returns empty list when no meetings exist."""
    response = client.get("/api/meetings/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_meeting_not_found(client):
    """GET /api/meetings/999 returns 404."""
    response = client.get("/api/meetings/999")
    assert response.status_code == 404


def test_create_subscriber(client):
    """POST /api/subscribers/ creates a subscriber."""
    response = client.post(
        "/api/subscribers/",
        json={"email": "test@amsterdam.nl", "language": "nl", "topics": ["housing"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@amsterdam.nl"
    assert data["language"] == "nl"


def test_create_duplicate_subscriber_reactivates(client):
    """Posting same email twice should reactivate rather than error."""
    payload = {"email": "dup@amsterdam.nl", "language": "nl"}
    r1 = client.post("/api/subscribers/", json=payload)
    r2 = client.post("/api/subscribers/", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]


def test_unsubscribe_invalid_token(client):
    """DELETE /api/subscribers/unsubscribe/bad-token returns 404."""
    response = client.delete("/api/subscribers/unsubscribe/bad-token-xyz")
    assert response.status_code == 404


def test_webhook_no_attachment(client):
    """POST /webhook/inbound with no attachment and no In-Reply-To → ignored."""
    response = client.post(
        "/webhook/inbound",
        data={
            "sender": "test@example.nl",
            "recipient": "ai@sandbox.mailgun.org",
            "subject": "Hello",
            "body-plain": "Geen bijlage",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
