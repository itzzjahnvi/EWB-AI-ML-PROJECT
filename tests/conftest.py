"""Shared fixtures. Tests only ever touch temporary SQLite files, never data/students.db."""

import os
import tempfile

# Must happen before the app is imported so even the lifespan hook uses a temp database.
_BOOTSTRAP_DIR = tempfile.mkdtemp(prefix="students_test_bootstrap_")
os.environ["DATABASE_URL"] = f"sqlite:///{_BOOTSTRAP_DIR}/bootstrap.db"
os.environ["AI_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.database.connection import build_engine, get_db, make_session_factory  # noqa: E402
from app.database.models import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.routers.ai_assistant import get_ollama_client  # noqa: E402


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test_students.db'}"


@pytest.fixture()
def engine(db_url):
    engine = build_engine(db_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return make_session_factory(engine)


def _override_db(app, session_factory):
    def _get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db


@pytest.fixture()
def client(session_factory):
    app = create_app()
    _override_db(app, session_factory)
    return TestClient(app)


@pytest.fixture()
def payload():
    """Factory for valid student payloads with unique defaults; override via kwargs."""
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        n = counter["n"]
        data = {
            "student_id": f"STU{1000 + n}",
            "name": f"Test Student {n}",
            "date_of_birth": "2005-06-15",
            "email": f"student{n}@example.com",
            "phone": "9876543210",
            "course": "Computer Science",
            "address": "Bengaluru",
            "enrollment_date": "2025-08-01",
        }
        data.update(overrides)
        return {k: v for k, v in data.items() if v is not ...}

    return _make


@pytest.fixture()
def create(client, payload):
    def _create(**overrides):
        response = client.post("/students", json=payload(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _create


class FakeOllama:
    """Stand-in for OllamaClient: no network, records every call."""

    def __init__(self, response="Mocked answer.", error=None, model="fake-model"):
        self.response = response
        self.error = error
        self.model = model
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.response


@pytest.fixture()
def fake_ollama():
    return FakeOllama()


@pytest.fixture()
def ai_client(session_factory, fake_ollama):
    app = create_app()
    _override_db(app, session_factory)
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, ai_enabled=True, database_url="sqlite://"
    )
    app.dependency_overrides[get_ollama_client] = lambda: fake_ollama
    return TestClient(app)
