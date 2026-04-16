"""Meeting list, detail, PDF, and segment endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Meeting, MeetingStatus, Segment
from schemas.meeting import MeetingDetail, MeetingListItem, SegmentOut, SpeakerSummary

router = APIRouter()


@router.get("/", response_model=list[MeetingListItem])
def list_meetings(
    status: str | None = None,
    topic: str | None = None,
    db: Session = Depends(get_db),
) -> list[MeetingListItem]:
    query = db.query(Meeting)
    if status:
        query = query.filter(Meeting.status == status)
    meetings = query.order_by(Meeting.created_at.desc()).all()

    result = []
    for m in meetings:
        # Filter by topic if requested
        if topic and (not m.topics or topic not in m.topics):
            continue
        result.append(
            MeetingListItem(
                id=m.id,
                title=m.title,
                municipality=m.municipality,
                date=m.date,
                status=m.status.value,
                topics=m.topics,
                agenda_item_count=len(m.summary_nl.get("agenda_items", [])) if m.summary_nl else 0,
            )
        )
    return result


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> MeetingDetail:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        municipality=meeting.municipality,
        date=meeting.date,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        status=meeting.status.value,
        topics=meeting.topics,
        summary_nl=meeting.summary_nl,
        pdf_path=meeting.pdf_path,
    )


@router.get("/{meeting_id}/segments", response_model=list[SegmentOut])
def get_meeting_segments(meeting_id: int, db: Session = Depends(get_db)) -> list[SegmentOut]:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    segments = (
        db.query(Segment)
        .filter(Segment.meeting_id == meeting_id)
        .order_by(Segment.order_idx.asc())
        .all()
    )
    return [SegmentOut.model_validate(segment) for segment in segments]


@router.get("/{meeting_id}/speakers", response_model=list[SpeakerSummary])
def get_meeting_speakers(meeting_id: int, db: Session = Depends(get_db)) -> list[SpeakerSummary]:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    speakers: dict[str, SpeakerSummary] = {}
    for segment in (
        db.query(Segment)
        .filter(Segment.meeting_id == meeting_id)
        .order_by(Segment.order_idx.asc())
        .all()
    ):
        if not segment.speaker:
            continue
        key = f"{segment.speaker}|{segment.party or ''}|{segment.role or ''}"
        if key not in speakers:
            speakers[key] = SpeakerSummary(
                id=key,
                speaker=segment.speaker,
                party=segment.party,
                role=segment.role,
                segment_count=0,
            )
        speakers[key].segment_count += 1
    return list(speakers.values())


@router.get("/{meeting_id}/summary/{lang}")
def get_translated_summary(meeting_id: int, lang: str, db: Session = Depends(get_db)) -> dict:
    """Return pre-translated summary for the given language."""
    from models import Translation

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if lang == "nl":
        return {"lang": "nl", "summary": meeting.summary_nl}

    translation = (
        db.query(Translation)
        .filter_by(meeting_id=meeting_id, target_lang=lang)
        .filter(Translation.summary_json.isnot(None))
        .first()
    )
    if not translation:
        raise HTTPException(status_code=404, detail=f"Translation for '{lang}' not ready yet")

    return {"lang": lang, "summary": translation.summary_json}


@router.get("/{meeting_id}/pdf")
def get_meeting_pdf(meeting_id: int, db: Session = Depends(get_db)) -> FileResponse:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(meeting.pdf_path, media_type="application/pdf", filename=f"meeting-{meeting_id}.pdf")


@router.post("/{meeting_id}/reprocess")
def reprocess_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Reset a failed meeting to pending for re-ingestion."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status == MeetingStatus.processing:
        raise HTTPException(status_code=409, detail="Meeting is currently being processed")
    meeting.status = MeetingStatus.pending
    meeting.error_message = None
    db.commit()
    return {"status": "queued"}
