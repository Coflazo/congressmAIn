"""Tests for DB models — use in-memory SQLite via conftest fixture."""

from datetime import datetime


def test_create_meeting(db):
    """Meeting can be created and retrieved."""
    from models import Meeting, MeetingStatus

    m = Meeting(title="Test Vergadering", status=MeetingStatus.pending)
    db.add(m)
    db.commit()
    db.refresh(m)

    assert m.id is not None
    assert m.status == MeetingStatus.pending
    retrieved = db.query(Meeting).filter_by(id=m.id).first()
    assert retrieved.title == "Test Vergadering"


def test_create_subscriber(db):
    """Subscriber can be created with all fields."""
    from models import Subscriber

    sub = Subscriber(
        email="test@example.nl",
        language="nl",
        topics=["housing", "climate"],
        frequency="immediate",
        unsubscribe_token="abc123",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    assert sub.id is not None
    assert sub.topics == ["housing", "climate"]
    assert sub.is_active is True


def test_meeting_segment_relationship(db):
    """Segments are deleted when Meeting is deleted (cascade)."""
    from models import Meeting, MeetingStatus, Segment

    m = Meeting(title="Cascade Test", status=MeetingStatus.ready)
    db.add(m)
    db.flush()

    seg = Segment(meeting_id=m.id, order_idx=0, text="Goedenavond.", speaker="Voorzitter")
    db.add(seg)
    db.commit()

    seg_id = seg.id
    db.delete(m)
    db.commit()

    assert db.query(Segment).filter_by(id=seg_id).first() is None


def test_translation_cache_unique_constraint(db):
    """Two translations with same hash+source+target should violate unique constraint."""
    from sqlalchemy.exc import IntegrityError

    from models import Translation

    t1 = Translation(
        meeting_id=0, target_lang="en", source_lang="nl",
        content_hash="abc123", source_text="Hallo", translated_text="Hello",
    )
    t2 = Translation(
        meeting_id=0, target_lang="en", source_lang="nl",
        content_hash="abc123", source_text="Hallo", translated_text="Hi",
    )
    db.add(t1)
    db.commit()
    db.add(t2)
    with pytest.raises(IntegrityError):
        db.commit()


import pytest
