"""Tests for the notifications API and helper."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.notifications import create_notification
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.notification import NotificationType
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

    user = User(email="notify@test.com", hashed_password="x", full_name="Notifier")
    other = User(email="other@test.com", hashed_password="x", full_name="Other")
    session.add_all([user, other])
    session.commit()
    session.refresh(user)
    session.refresh(other)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as c:
        yield c, session, user, other

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_list_returns_only_own_notifications(client):
    c, session, user, other = client
    create_notification(session, user.id, NotificationType.GUARD_BLOCK, "Blocked", "Injection attempt")
    create_notification(session, other.id, NotificationType.GUARD_BLOCK, "Other", "Not yours")

    resp = c.get("/api/v1/notifications")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["title"] == "Blocked"
    assert payload[0]["is_read"] is False


def test_unread_only_filter(client):
    c, session, user, _ = client
    first = create_notification(session, user.id, NotificationType.DOCUMENT_GENERATED, "One", "First")
    create_notification(session, user.id, NotificationType.DOCUMENT_GENERATED, "Two", "Second")

    assert c.post("/api/v1/notifications/read", json={"ids": [first.id]}).status_code == 204

    resp = c.get("/api/v1/notifications?unread_only=true")
    assert resp.status_code == 200
    titles = [n["title"] for n in resp.json()]
    assert titles == ["Two"]


def test_mark_read_only_affects_current_user(client):
    c, session, user, other = client
    foreign = create_notification(session, other.id, NotificationType.GUARD_BLOCK, "Other", "Not yours")

    assert c.post("/api/v1/notifications/read", json={"ids": [foreign.id]}).status_code == 204
    session.refresh(foreign)
    assert foreign.is_read is False


def test_delete_own_notification(client):
    c, session, user, _ = client
    notification = create_notification(session, user.id, NotificationType.COMPLIANCE_DRIFT, "Drift", "Score dropped")

    assert c.delete(f"/api/v1/notifications/{notification.id}").status_code == 204
    assert c.get("/api/v1/notifications").json() == []


def test_delete_foreign_notification_returns_404(client):
    c, session, user, other = client
    foreign = create_notification(session, other.id, NotificationType.COMPLIANCE_DRIFT, "Drift", "Not yours")

    assert c.delete(f"/api/v1/notifications/{foreign.id}").status_code == 404
