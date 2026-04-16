from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import settings

# SQLite: check_same_thread=False needed for multi-threaded FastAPI.
# StaticPool required for in-memory SQLite so all connections share the same DB.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

if settings.database_url == "sqlite:///:memory:":
    engine = create_engine(settings.database_url, connect_args=connect_args, poolclass=StaticPool)
else:
    engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call multiple times (idempotent)."""
    import models  # noqa: F401 — registers models with Base.metadata

    Base.metadata.create_all(bind=engine)
    print("Database initialised.")
