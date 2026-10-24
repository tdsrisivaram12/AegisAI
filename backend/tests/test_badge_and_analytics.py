"""Tests for the public badge endpoint and the analytics endpoints."""

import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.document import Document, DocumentType
from app.models.user import User


@pytest.fixture
def ctx():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    user = User(email="analytics@test.com", hashed_password="x", full_name="Analyst")
    session.add(user)
    session.flush()

    compliant = AISystem(
        owner_id=user.id,
        name="Alpha",
        risk_level=RiskLevel.HIGH,
        compliance_status=ComplianceStatus.COMPLIANT,
        compliance_score=90.0,
    )
    in_progress = AISystem(
        owner_id=user.id,
        name="Beta",
        risk_level=RiskLevel.MINIMAL,
        compliance_status=ComplianceStatus.IN_PROGRESS,
        compliance_score=50.0,
    )
    session.add_all([compliant, in_progress])
    session.flush()

    session.add(Document(
        owner_id=user.id,
        ai_system_id=compliant.id,
        title="Technical docs",
        document_type=DocumentType.TECHNICAL_DOCUMENTATION,
    ))
    session.add(ComplianceSnapshot(
        ai_system_id=compliant.id,
        compliance_score=80,
        compliance_status=ComplianceStatus.IN_PROGRESS.value,
        risk_level=RiskLevel.HIGH.value,
        snapshotted_at=datetime.utcnow() - timedelta(days=5),
    ))
    session.add(ComplianceSnapshot(
        ai_system_id=compliant.id,
        compliance_score=90,
        compliance_status=ComplianceStatus.COMPLIANT.value,
        risk_level=RiskLevel.HIGH.value,
        snapshotted_at=datetime.utcnow(),
    ))
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, session, user, compliant

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class TestBadgeEndpoint:
    def test_badge_returns_svg(self, ctx):
        client, _, _, system = ctx
        app.dependency_overrides.pop(get_current_user, None)
        resp = client.get(f"/api/v1/badge/{system.id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/svg+xml")
        assert resp.text.startswith("<svg")

    def test_badge_json_format(self, ctx):
        client, _, _, system = ctx
        resp = client.get(f"/api/v1/badge/{system.id}?format=json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["system_name"] == "Alpha"
        assert body["risk_level"] == "high"
        assert body["compliance_status"] == "compliant"

    def test_missing_system_returns_404(self, ctx):
        client, *_ = ctx
        assert client.get("/api/v1/badge/9999").status_code == 404


class TestAnalyticsEndpoints:
    def test_summary_aggregates(self, ctx):
        client, *_ = ctx
        resp = client.get("/api/v1/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_systems"] == 2
        assert body["by_risk_level"]["high"] == 1
        assert body["by_compliance_status"]["compliant"] == 1
        assert body["documents_generated"] == 1
        assert body["average_compliance_score"] == 70.0

    def test_timeline_returns_snapshots_in_order(self, ctx):
        client, _, _, system = ctx
        resp = client.get(f"/api/v1/analytics/compliance-timeline?system_id={system.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ai_system_name"] == "Alpha"
        scores = [s["compliance_score"] for s in body["snapshots"]]
        assert scores == [80, 90]

    def test_timeline_unknown_system_returns_404(self, ctx):
        client, *_ = ctx
        assert client.get("/api/v1/analytics/compliance-timeline?system_id=9999").status_code == 404
