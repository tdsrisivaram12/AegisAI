"""Tests for search/filter and pagination on GET /api/v1/ai-systems."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.user import User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    user = User(email="filters@test.com", hashed_password="x", full_name="Filter Tester")
    session.add(user)
    session.flush()

    session.add_all([
        AISystem(owner_id=user.id, name="Alpha System", risk_level=RiskLevel.HIGH,
                 compliance_status=ComplianceStatus.COMPLIANT),
        AISystem(owner_id=user.id, name="Beta System", risk_level=RiskLevel.MINIMAL,
                 compliance_status=ComplianceStatus.NOT_STARTED),
        AISystem(owner_id=user.id, name="Gamma System", risk_level=RiskLevel.HIGH,
                 compliance_status=ComplianceStatus.IN_PROGRESS),
    ])
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class TestAISystemsFilters:
    def test_plain_list_response_is_array(self, client):
        resp = client.get("/api/v1/ai-systems/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 3

    def test_search_matches_name_substring(self, client):
        resp = client.get("/api/v1/ai-systems/?search=al")
        assert resp.status_code == 200
        assert [s["name"] for s in resp.json()] == ["Alpha System"]

    def test_filter_by_risk_level(self, client):
        resp = client.get("/api/v1/ai-systems/?risk_level=high")
        assert resp.status_code == 200
        assert {s["name"] for s in resp.json()} == {"Alpha System", "Gamma System"}

    def test_filter_by_compliance_status(self, client):
        resp = client.get("/api/v1/ai-systems/?compliance_status=in_progress")
        assert resp.status_code == 200
        assert [s["name"] for s in resp.json()] == ["Gamma System"]

    def test_invalid_risk_level_returns_400(self, client):
        resp = client.get("/api/v1/ai-systems/?risk_level=banana")
        assert resp.status_code == 400
        assert "risk_level" in resp.json()["detail"].lower()

    def test_invalid_compliance_status_returns_400(self, client):
        resp = client.get("/api/v1/ai-systems/?compliance_status=banana")
        assert resp.status_code == 400
        assert "compliance_status" in resp.json()["detail"].lower()

    def test_page_and_limit_return_envelope(self, client):
        resp = client.get("/api/v1/ai-systems/?page=1&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"items", "total", "page", "limit"}
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["limit"] == 2
        assert len(body["items"]) == 2

    def test_page_two_returns_remainder(self, client):
        body = client.get("/api/v1/ai-systems/?page=2&limit=2").json()
        assert body["total"] == 3
        assert len(body["items"]) == 1
