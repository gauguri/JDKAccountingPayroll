"""Test fixtures: a fresh SQLite DB and an authenticated client per test."""
import os
import tempfile
import uuid

import pytest

# Point the app at a throwaway SQLite file BEFORE importing it.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.db import init_db, SessionLocal  # noqa: E402
from app.services.tax_rules import seed_sample_tax_rules  # noqa: E402

init_db()
# The startup seeder only runs under a live server; seed here so payroll tests
# have tax tables to read.
_seed_db = SessionLocal()
try:
    seed_sample_tax_rules(_seed_db)
finally:
    _seed_db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def company(client):
    """Register a fresh user+company and return (client, company_id)."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "supersecret123",
        "full_name": "Test Owner", "company_name": "Test Signs Co",
        "business_type": "c_corp", "state": "NJ",
    })
    assert r.status_code == 201, r.text
    companies = client.get("/api/companies").json()
    return companies[0]["id"]


def accounts_by_name(client, company_id):
    rows = client.get(f"/api/companies/{company_id}/accounts").json()
    return {a["name"]: a["id"] for a in rows}
