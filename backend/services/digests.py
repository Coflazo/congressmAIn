"""Digest rendering and delivery helpers."""

from __future__ import annotations

import json
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from config import settings
from models import ChatMessage, DigestDelivery, DigestDeliveryStatus, Meeting, Subscriber
from services.translate import translate_async

EMAILS_DIR = (Path(__file__).resolve().parents[2] / "emails").resolve()
OUT_DIR = EMAILS_DIR / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

env = Environment(
    loader=FileSystemLoader(str(EMAILS_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _message_id(prefix: str, meeting_id: int, language: str) -> str:
    return f"<{prefix}-{meeting_id}-{language}-{uuid.uuid4().hex[:12]}@ai020.local>"


def _meeting_summary_for_language(meeting: Meeting, lang: str) -> dict[str, Any]:
    if lang == "nl" or not meeting.translations:
        return meeting.summary_nl or {}
    for translation in meeting.translations:
        if translation.target_lang == lang and translation.summary_json:
            return translation.summary_json
    return meeting.summary_nl or {}


def _speaker_details(meeting: Meeting) -> list[dict[str, Any]]:
    speakers: dict[str, dict[str, Any]] = {}
    for segment in meeting.segments:
        if not segment.speaker:
            continue
        key = f"{segment.speaker}|{segment.party or ''}|{segment.role or ''}"
        entry = speakers.setdefault(
            key,
            {
                "speaker": segment.speaker,
                "party": segment.party,
                "role": segment.role,
                "quotes": [],
            },
        )
        if len(entry["quotes"]) < 2:
            entry["quotes"].append(segment.text[:280])
    return list(speakers.values())[:8]


def _render_digest_html(meeting: Meeting, subscriber: Subscriber, public_base_url: str) -> tuple[str, str]:
    summary = _meeting_summary_for_language(meeting, subscriber.language)
    template = env.get_template("digest.html.j2")
    title = meeting.title
    decisions = (summary.get("agenda_items") or [])[:3]
    html = template.render(
        meeting=meeting,
        summary=summary,
        subscriber=subscriber,
        decisions=decisions,
        speakers=_speaker_details(meeting),
        public_base_url=public_base_url.rstrip("/"),
        unsubscribe_url=f"{public_base_url.rstrip('/')}/unsubscribe/{subscriber.unsubscribe_token}",
    )
    subject = f"AI020 briefing: {title}"
    return html, subject


async def _send_via_mailgun(recipient: str, subject: str, html: str, message_id: str, in_reply_to: str | None = None) -> None:
    if not settings.mailgun_api_key or not settings.mailgun_domain:
        raise RuntimeError("Mailgun not configured")
    data = {
        "from": settings.default_from_email,
        "to": recipient,
        "subject": subject,
        "html": html,
        "h:Message-Id": message_id,
    }
    if in_reply_to:
        data["h:In-Reply-To"] = in_reply_to
        data["h:References"] = in_reply_to

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages",
            data=data,
            auth=("api", settings.mailgun_api_key),
        )
        response.raise_for_status()


async def deliver_meeting_digest(meeting_id: int, db: Session) -> list[DigestDelivery]:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise ValueError(f"Meeting {meeting_id} not found")

    subscribers = (
        db.query(Subscriber)
        .filter(Subscriber.is_active.is_(True))
        .order_by(Subscriber.email.asc())
        .all()
    )
    deliveries: list[DigestDelivery] = []
    for subscriber in subscribers:
        html, subject = _render_digest_html(meeting, subscriber, settings.public_base_url)
        message_id = _message_id("digest", meeting.id, subscriber.language)
        output_path = OUT_DIR / f"meeting-{meeting.id}-{subscriber.language}-{subscriber.email.replace('@', '_at_')}.html"

        delivery = DigestDelivery(
            meeting_id=meeting.id,
            subscriber_id=subscriber.id,
            recipient_email=subscriber.email,
            language=subscriber.language,
            message_id=message_id,
            subject=subject,
            status=DigestDeliveryStatus.rendered if not settings.mailgun_api_key else DigestDeliveryStatus.sent,
            output_path=str(output_path),
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        if settings.mailgun_api_key:
            try:
                await _send_via_mailgun(subscriber.email, subject, html, message_id)
            except Exception as exc:
                delivery.status = DigestDeliveryStatus.failed
                delivery.error_message = str(exc)
                db.commit()
            else:
                delivery.status = DigestDeliveryStatus.sent
                db.commit()
        else:
            output_path.write_text(html, encoding="utf-8")
        deliveries.append(delivery)
    return deliveries


async def deliver_chat_reply(
    *,
    meeting: Meeting,
    recipient_email: str,
    reply_to_message_id: str,
    question: str,
    answer: str,
    citations: list[int],
    language: str,
    db: Session,
) -> DigestDelivery:
    template = env.get_template("chat_reply.html.j2")
    html = template.render(
        meeting=meeting,
        answer=answer,
        citations=citations,
        question=question,
        public_base_url=settings.public_base_url.rstrip("/"),
    )
    subject = f"Re: AI020 briefing: {meeting.title}"
    message_id = _message_id("reply", meeting.id, language)
    output_path = OUT_DIR / f"reply-{meeting.id}-{language}-{recipient_email.replace('@', '_at_')}.html"

    delivery = DigestDelivery(
        meeting_id=meeting.id,
        subscriber_id=None,
        recipient_email=recipient_email,
        language=language,
        message_id=message_id,
        subject=subject,
        status=DigestDeliveryStatus.rendered if not settings.mailgun_api_key else DigestDeliveryStatus.sent,
        output_path=str(output_path),
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    if settings.mailgun_api_key:
        try:
            await _send_via_mailgun(recipient_email, subject, html, message_id, in_reply_to=reply_to_message_id)
        except Exception as exc:
            delivery.status = DigestDeliveryStatus.failed
            delivery.error_message = str(exc)
            db.commit()
        else:
            delivery.status = DigestDeliveryStatus.sent
            db.commit()
    else:
        output_path.write_text(html, encoding="utf-8")
    return delivery


async def build_chat_reply(
    *,
    meeting: Meeting,
    question: str,
    answer_nl: str,
    citations: list[int],
    user_language: str,
    db: Session,
) -> tuple[str, list[int]]:
    answer = answer_nl
    if user_language != "nl":
        answer = await translate_async(answer_nl, source="nl", target=user_language, db=db, meeting_id=meeting.id)
    db.add(
        ChatMessage(
            meeting_id=meeting.id,
            role="assistant",
            content=answer,
            language=user_language,
            citations=citations,
        )
    )
    db.commit()
    return answer, citations


def email_preview_payload(meeting: Meeting, language: str) -> dict[str, Any]:
    summary = _meeting_summary_for_language(meeting, language)
    return {
        "title": meeting.title,
        "date": meeting.date,
        "summary": json.dumps(summary, ensure_ascii=False),
    }
