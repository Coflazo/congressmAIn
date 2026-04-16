"""Inbound email webhook — Mailgun multipart payload."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import DigestDelivery, Meeting
from services.digests import build_chat_reply, deliver_chat_reply

router = APIRouter()


@router.post("/inbound")
async def inbound_email(
    background_tasks: BackgroundTasks,
    sender: str = Form(default=""),
    recipient: str = Form(default=""),
    subject: str = Form(default=""),
    body_plain: str = Form(default="", alias="body-plain"),
    message_id: str = Form(default="", alias="Message-Id"),
    in_reply_to: str = Form(default="", alias="In-Reply-To"),
    attachment_1: UploadFile | None = File(default=None, alias="attachment-1"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    has_pdf = attachment_1 is not None and bool(attachment_1.filename) and attachment_1.filename.lower().endswith(".pdf")

    if has_pdf and attachment_1 is not None:
        content = await attachment_1.read()
        suffix = Path(attachment_1.filename or "meeting.pdf").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="/tmp") as tmp:
            tmp.write(content)
            temp_path = tmp.name

        background_tasks.add_task(
            _run_ingestion_task,
            pdf_path=temp_path,
            source_email=sender,
            subject=subject or attachment_1.filename or "Raadsvergadering",
        )
        return JSONResponse(
            {"status": "queued", "intent": "new-meeting", "sender": sender, "recipient": recipient},
            status_code=200,
        )

    if in_reply_to:
        delivery = db.query(DigestDelivery).filter(DigestDelivery.message_id == in_reply_to).first()
        if not delivery:
            return JSONResponse({"status": "ignored", "reason": "unknown-thread"}, status_code=200)
        background_tasks.add_task(
            _run_email_qa_task,
            meeting_id=delivery.meeting_id,
            question=body_plain,
            reply_to_message_id=in_reply_to,
            sender_email=sender,
        )
        return JSONResponse({"status": "queued", "intent": "qa-reply"}, status_code=200)

    _ = message_id
    return JSONResponse({"status": "ignored"}, status_code=200)


def _run_ingestion_task(pdf_path: str, source_email: str, subject: str) -> None:
    from pipeline.ingest import ingest_pdf_sync

    ingest_pdf_sync(pdf_path=pdf_path, source_email=source_email, subject=subject, deliver=True)
    try:
        Path(pdf_path).unlink(missing_ok=True)
    except OSError:
        pass


def _run_email_qa_task(meeting_id: int, question: str, reply_to_message_id: str, sender_email: str) -> None:
    from routers.chat import _CHAT_RESPONSE_SCHEMA, _SYSTEM_PROMPT, _retrieve_segments
    from services import openai_client
    from services.translate import translate_sync

    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting is None:
            return

        user_lang = "nl"
        question_nl = question
        if sender_email and not question.strip():
            question_nl = "Kun je de belangrijkste besluiten kort samenvatten?"
        top_segments = _retrieve_segments(meeting_id, question_nl, db)
        if not top_segments:
            answer = "Ik kon geen bruikbare fragmenten vinden in deze vergadering."
            citations: list[int] = []
        else:
            context = "\n\n---\n\n".join(
                f"[segment_id={segment.id}] {segment.speaker or 'Onbekend'}:\n{segment.text}"
                for segment in top_segments
            )
            completion = openai_client.chat_completion(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Fragmenten:\n\n{context}\n\nVraag: {question_nl}"},
                ],
                response_format=_CHAT_RESPONSE_SCHEMA,
            )
            payload = openai_client.extract_json(completion)
            answer = payload["answer"]
            citations = [int(value) for value in payload.get("citations", [])]

        answer, citations = asyncio.run(
            build_chat_reply(
                meeting=meeting,
                question=question,
                answer_nl=answer,
                citations=citations,
                user_language=user_lang,
                db=db,
            )
        )
        asyncio.run(
            deliver_chat_reply(
                meeting=meeting,
                recipient_email=sender_email,
                reply_to_message_id=reply_to_message_id,
                question=question,
                answer=answer,
                citations=citations,
                language=user_lang,
                db=db,
            )
        )
    finally:
        db.close()
