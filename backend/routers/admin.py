"""Admin panel routes — JWT-gated."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Admin, DigestDelivery, DigestDeliveryStatus, Meeting, MeetingStatus, Subscriber

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/token")


# ── Auth helpers ───────────────────────────────────────────────────────────────


def _create_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": email, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Admin:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email: str | None = payload.get("sub")
        if not email:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    admin = db.query(Admin).filter_by(email=email).first()
    if not admin:
        raise credentials_exc
    return admin


# ── Endpoints ──────────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    admin = db.query(Admin).filter_by(email=form.username).first()
    if not admin or not pwd_context.verify(form.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=_create_token(admin.email))


class MetricsResponse(BaseModel):
    meetings_processed: int
    meetings_processing: int
    meetings_failed: int
    avg_processing_time_seconds: float
    translation_cache_hit_rate: float
    digest_delivery_success: float
    active_subscribers: int
    top_topics: list[dict]


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    _admin: Admin = Depends(_get_current_admin),
    db: Session = Depends(get_db),
) -> MetricsResponse:
    processed = db.query(func.count(Meeting.id)).filter(Meeting.status == MeetingStatus.ready).scalar() or 0
    processing = db.query(func.count(Meeting.id)).filter(Meeting.status == MeetingStatus.processing).scalar() or 0
    failed = db.query(func.count(Meeting.id)).filter(Meeting.status == MeetingStatus.failed).scalar() or 0
    subscribers = db.query(func.count(Subscriber.id)).filter(Subscriber.is_active.is_(True)).scalar() or 0
    ready_meetings = db.query(Meeting).filter(Meeting.status == MeetingStatus.ready).all()

    durations = []
    for meeting in ready_meetings:
        if meeting.processing_started_at and meeting.processing_finished_at:
            durations.append((meeting.processing_finished_at - meeting.processing_started_at).total_seconds())
    avg_processing_time = round(sum(durations) / len(durations), 2) if durations else 0.0

    translate_log = (Path(__file__).resolve().parents[1] / "logs" / "translate.log")
    cached = total = 0
    if translate_log.exists():
        for line in translate_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            total += 1
            if entry.get("cached"):
                cached += 1
    cache_hit_rate = round((cached / total) * 100, 2) if total else 0.0

    deliveries = db.query(DigestDelivery).all()
    successful_deliveries = sum(
        1 for delivery in deliveries if delivery.status in (DigestDeliveryStatus.rendered, DigestDeliveryStatus.sent)
    )
    digest_delivery_success = round((successful_deliveries / len(deliveries)) * 100, 2) if deliveries else 0.0

    topic_counts: dict[str, int] = {}
    for meeting in ready_meetings:
        for topic in meeting.topics or []:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return MetricsResponse(
        meetings_processed=processed,
        meetings_processing=processing,
        meetings_failed=failed,
        avg_processing_time_seconds=avg_processing_time,
        translation_cache_hit_rate=cache_hit_rate,
        digest_delivery_success=digest_delivery_success,
        active_subscribers=subscribers,
        top_topics=top_topics,
    )


@router.get("/meetings")
def admin_meetings(
    _admin: Admin = Depends(_get_current_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).limit(100).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "date": m.date,
            "status": m.status.value,
            "error_message": m.error_message,
        }
        for m in meetings
    ]


@router.get("/subscribers")
def admin_subscribers(
    _admin: Admin = Depends(_get_current_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    subs = db.query(Subscriber).order_by(Subscriber.created_at.desc()).limit(200).all()
    return [
        {
            "id": s.id,
            "email": s.email,
            "language": s.language,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat(),
        }
        for s in subs
    ]


@router.post("/seed")
def seed_admin(db: Session = Depends(get_db)) -> dict:
    """Create initial admin from env vars. Safe to call multiple times."""
    if not settings.admin_email or not settings.admin_password_hash:
        raise HTTPException(status_code=400, detail="ADMIN_EMAIL and ADMIN_PASSWORD_HASH must be set in .env")
    existing = db.query(Admin).filter_by(email=settings.admin_email).first()
    if existing:
        return {"status": "already_exists", "email": settings.admin_email}
    admin = Admin(email=settings.admin_email, password_hash=settings.admin_password_hash)
    db.add(admin)
    db.commit()
    return {"status": "created", "email": settings.admin_email}
