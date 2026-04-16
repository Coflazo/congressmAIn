from __future__ import annotations

import secrets

from database import SessionLocal, init_db
from models import Subscriber

DEFAULT_SUBSCRIBERS = [
    ("demo-nl@ai020.local", "nl"),
    ("demo-en@ai020.local", "en"),
    ("demo-tr@ai020.local", "tr"),
    ("demo-pl@ai020.local", "pl"),
    ("demo-uk@ai020.local", "uk"),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for email, language in DEFAULT_SUBSCRIBERS:
            existing = db.query(Subscriber).filter_by(email=email).first()
            if existing:
                continue
            db.add(
                Subscriber(
                    email=email,
                    language=language,
                    topics=[],
                    frequency="immediate",
                    unsubscribe_token=secrets.token_urlsafe(32),
                )
            )
        db.commit()
        print("Seeded demo subscribers.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
