"""Subscriber CRUD endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Subscriber
from schemas.meeting import SubscriberCreate, SubscriberOut

router = APIRouter()


@router.post("/", response_model=SubscriberOut, status_code=201)
def create_subscriber(payload: SubscriberCreate, db: Session = Depends(get_db)) -> SubscriberOut:
    existing = db.query(Subscriber).filter_by(email=payload.email).first()
    if existing:
        # Re-activate if previously unsubscribed
        existing.is_active = True
        existing.language = payload.language
        existing.topics = payload.topics
        existing.frequency = payload.frequency
        db.commit()
        db.refresh(existing)
        return SubscriberOut.model_validate(existing)

    sub = Subscriber(
        email=payload.email,
        language=payload.language,
        topics=payload.topics,
        frequency=payload.frequency,
        unsubscribe_token=secrets.token_urlsafe(32),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriberOut.model_validate(sub)


@router.get("/{email}", response_model=SubscriberOut)
def get_subscriber(email: str, db: Session = Depends(get_db)) -> SubscriberOut:
    sub = db.query(Subscriber).filter_by(email=email).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return SubscriberOut.model_validate(sub)


@router.delete("/unsubscribe/{token}")
def unsubscribe(token: str, db: Session = Depends(get_db)) -> dict:
    sub = db.query(Subscriber).filter_by(unsubscribe_token=token).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe token")
    sub.is_active = False
    db.commit()
    return {"status": "unsubscribed", "email": sub.email}
