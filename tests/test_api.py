import os
os.environ["IGD_API_KEY"] = "test"
os.environ["IGD_DB_PATH"] = "./test_jobs.db"

from fastapi.testclient import TestClient
from app import worker
from app.main import app

H = {"X-API-Key": "test"}


def test_health():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}


def test_requires_key():
    with TestClient(app) as c:
        assert c.post("/api/v1/jobs", json={"username": "nasa"}).status_code == 401


def test_rejects_bad_url():
    with TestClient(app) as c:
        r = c.post("/api/v1/jobs", json={"url": "[example.com](https://example.com)"}, headers=H)
        assert r.status_code == 422


def test_creates_job(monkeypatch):
    monkeypatch.setattr(worker, "submit", lambda jid: None)  # no network in tests
    with TestClient(app) as c:
        r = c.post("/api/v1/jobs",
                   json={"url": "[instagram.com](https://www.instagram.com/p/C0abcDEF123/)"},
                   headers=H)
        assert r.status_code == 202
        job = r.json()
        assert job["type"] == "post" and job["target"] == "C0abcDEF123"
        assert c.get(f"/api/v1/jobs/{job['id']}", headers=H).json()["status"] == "queued"


def test_path_traversal_blocked():
    with TestClient(app) as c:
        assert c.get("/api/v1/files/../jobs.db", headers=H).status_code == 404
