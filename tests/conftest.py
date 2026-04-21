"""Shared test fixtures."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add backend to path so tests can import it
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Use SQLite in-memory for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FALLBACK_SERVER_URL", "http://localhost:4000")
os.environ.setdefault("FALLBACK_MODEL", "t0-deepseek")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")  # kept so old imports don't crash
os.environ.setdefault("LIBRETRANSLATE_URL", "http://localhost:5000")


@pytest.fixture()
def db():
    """In-memory SQLite session for unit tests."""
    from database import Base, SessionLocal, engine
    import models  # noqa: F401 — register models

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    """Shared FastAPI test client with overridden DB dependency."""
    from main import app
    from database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_pdf() -> Path:
    path = Path(__file__).parent.parent / "brief" / "real-transcript-20210527.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not available")
    return path
