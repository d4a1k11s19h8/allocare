"""
AlloCare Test Suite: conftest.py
Shared fixtures for all test modules.
"""
import os
import sys
import pytest

# Ensure backend dir is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force local data store (not firebase)
os.environ["DEPLOYMENT"] = "render"
# Set a dummy Gemini key so the app doesn't crash on import
os.environ.setdefault("GEMINI_API_KEY", "test_dummy_key_for_unit_tests")

from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    """FastAPI test client: shared across all tests in a session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def seed_data(client):
    """Ensure demo data is seeded before the test session."""
    resp = client.post("/api/demo/seed")
    assert resp.status_code == 200


@pytest.fixture
def first_need_id(client):
    """Return the ID of the first open need report."""
    resp = client.get("/api/needs?status=open&limit=1")
    needs = resp.json()["needs"]
    assert len(needs) > 0, "No open needs found: seed data may have failed"
    return needs[0]["id"]


@pytest.fixture
def first_volunteer_id(client):
    """Return the ID of the first available volunteer."""
    resp = client.get("/api/volunteers?limit=1")
    vols = resp.json()["volunteers"]
    assert len(vols) > 0, "No volunteers found: seed data may have failed"
    return vols[0]["id"]
