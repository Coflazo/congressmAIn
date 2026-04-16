from __future__ import annotations

import io
from pathlib import Path

from fixtures import INBOUND_EMAIL_PAYLOAD


async def _noop_translate_summary(summary, db, meeting_id):
    return {}


def test_extract_real_pdf_text(sample_pdf):
    from pipeline.ingest import extract_text

    pages, text = extract_text(str(sample_pdf))
    assert len(pages) > 0
    assert "Gemeente Amsterdam" in text


def test_ingest_sample_transcript_creates_summary_and_segments(db, monkeypatch):
    from models import Segment
    from pipeline import ingest

    monkeypatch.setattr(ingest, "translate_summary", _noop_translate_summary)
    transcript_path = Path(__file__).parent.parent / "brief" / "sample-transcript.txt"

    meeting = ingest.ingest_pdf_sync(
        pdf_path=str(transcript_path),
        subject="Sample transcript",
        deliver=False,
    )

    assert meeting.id is not None
    assert meeting.summary_nl is not None
    assert meeting.summary_nl["agenda_items"]
    assert db.query(Segment).filter(Segment.meeting_id == meeting.id).count() > 0


def test_webhook_pdf_creates_digest_html(client, db, monkeypatch, tmp_path, sample_pdf):
    from models import Meeting, Subscriber
    from pipeline import ingest
    from services import digests

    monkeypatch.setattr(ingest, "translate_summary", _noop_translate_summary)
    monkeypatch.setattr(digests, "OUT_DIR", tmp_path)

    subscriber = Subscriber(
        email="resident@example.nl",
        language="nl",
        topics=["housing"],
        frequency="immediate",
        unsubscribe_token="token-123",
    )
    db.add(subscriber)
    db.commit()

    payload = dict(INBOUND_EMAIL_PAYLOAD)
    response = client.post(
        "/webhook/inbound",
        data=payload,
        files={"attachment-1": ("real-transcript-20210527.pdf", sample_pdf.read_bytes(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"

    meeting = db.query(Meeting).order_by(Meeting.id.desc()).first()
    assert meeting is not None
    rendered = list(tmp_path.glob("meeting-*.html"))
    assert rendered
    assert "AI020 briefing" in rendered[0].read_text(encoding="utf-8")
