from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

client = TestClient(app)


class FakeSession:
    """Stands in for a database session so tests need no real PostgreSQL."""

    def __init__(self, fail: bool = False):
        self.fail = fail

    def execute(self, *_args, **_kwargs):
        if self.fail:
            raise RuntimeError("connection refused")

    def close(self):
        pass


def test_liveness_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_ok_when_database_reachable():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_readiness_503_when_database_down():
    app.dependency_overrides[get_db] = lambda: FakeSession(fail=True)
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
