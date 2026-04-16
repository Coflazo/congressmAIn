"""SQLAlchemy ORM models — Postgres-compatible schema via SQLAlchemy."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class MeetingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    municipality: Mapped[str | None] = mapped_column(String(255))
    date: Mapped[str | None] = mapped_column(String(10))  # YYYY-MM-DD
    start_time: Mapped[str | None] = mapped_column(String(5))  # HH:MM
    end_time: Mapped[str | None] = mapped_column(String(5))
    pdf_path: Mapped[str | None] = mapped_column(String(1024))
    source_email: Mapped[str | None] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus), default=MeetingStatus.pending, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    processing_finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Structured output (Dutch) stored as JSON
    summary_nl: Mapped[dict | None] = mapped_column(JSON)  # full MeetingSummary JSON
    topics: Mapped[list | None] = mapped_column(JSON)  # list of topic strings

    segments: Mapped[list["Segment"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    translations: Mapped[list["Translation"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    digest_deliveries: Mapped[list["DigestDelivery"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
    )


class Segment(Base):
    """A speaker turn in the transcript."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(255))
    party: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    # Bounding box for PDF viewer highlight: [x0, y0, x1, y1]
    bbox: Mapped[list | None] = mapped_column(JSON)
    intent: Mapped[str | None] = mapped_column(String(50))  # statement|question|motion|vote

    meeting: Mapped[Meeting] = relationship(back_populates="segments")


class Translation(Base):
    """Pre-translated summary fields (LibreTranslate output)."""

    __tablename__ = "translations"
    __table_args__ = (UniqueConstraint("content_hash", "source_lang", "target_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    target_lang: Mapped[str] = mapped_column(String(5), nullable=False)  # en|tr|pl|uk
    source_lang: Mapped[str] = mapped_column(String(5), default="nl", nullable=False)
    # SHA256 of source text — used as cache key
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meeting: Mapped[Meeting] = relationship(back_populates="translations")

    # Full translated summary JSON (only set on the top-level summary translation)
    summary_json: Mapped[dict | None] = mapped_column(JSON)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(5), default="nl")
    topics: Mapped[list | None] = mapped_column(JSON)  # list of topic strings
    frequency: Mapped[str] = mapped_column(String(20), default="immediate")  # immediate|weekly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Signed token for unsubscribe links
    unsubscribe_token: Mapped[str | None] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    digest_deliveries: Mapped[list["DigestDelivery"]] = relationship(back_populates="subscriber")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20))  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="nl")
    citations: Mapped[list | None] = mapped_column(JSON)  # list of segment_ids
    # For email-reply chat: In-Reply-To header value
    reply_to_message_id: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meeting: Mapped[Meeting] = relationship(back_populates="chat_messages")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DigestDeliveryStatus(str, enum.Enum):
    rendered = "rendered"
    sent = "sent"
    failed = "failed"


class DigestDelivery(Base):
    __tablename__ = "digest_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    subscriber_id: Mapped[int | None] = mapped_column(ForeignKey("subscribers.id"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="nl")
    message_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[DigestDeliveryStatus] = mapped_column(
        Enum(DigestDeliveryStatus),
        default=DigestDeliveryStatus.rendered,
        nullable=False,
    )
    output_path: Mapped[str | None] = mapped_column(String(1024))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meeting: Mapped[Meeting] = relationship(back_populates="digest_deliveries")
    subscriber: Mapped[Subscriber | None] = relationship(back_populates="digest_deliveries")
