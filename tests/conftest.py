"""Test fixtures: every test gets a fresh temporary SQLite database."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture()
def session_factory(db_path):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def _override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    # Not used as a context manager on purpose: that would run the start-up hook
    # (init_db) against the REAL database. Tests only use the temporary one.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def payload():
    return {
        "student_id": "STU-1001",
        "full_name": "Aarav Sample",
        "date_of_birth": "2004-05-17",
        "email": "aarav.sample@example.com",
        "phone": "+91 98765 43210",
        "course": "Computer Science",
        "address": "12 Sample Street, Example City",
        "enrollment_date": "2024-08-01",
    }


@pytest.fixture()
def make_student(client, payload):
    def _make(**overrides):
        body = {**payload, **overrides}
        resp = client.post("/students", json=body)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
