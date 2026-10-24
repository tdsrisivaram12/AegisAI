"""
Analytics API — compliance score timelines and aggregate stats.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Endpoints:
  - GET /analytics/compliance-timeline?system_id={id}&days=30
  - GET /analytics/summary
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.document import Document
from app.models.user import User
from app.schemas.analytics import ComplianceSnapshotResponse, ComplianceTimelineResponse

router = APIRouter()


@router.get("/compliance-timeline", response_model=ComplianceTimelineResponse)
def get_compliance_timeline(
    system_id: int,
    days: int = Query(30, ge=1, le=365, description="How many days of history to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return daily compliance snapshots for one of the current user's systems."""
    ai_system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id,
    ).first()

    if not ai_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    since = datetime.utcnow() - timedelta(days=days)
    snapshots = (
        db.query(ComplianceSnapshot)
        .filter(
            ComplianceSnapshot.ai_system_id == ai_system.id,
            ComplianceSnapshot.snapshotted_at >= since,
        )
        .order_by(ComplianceSnapshot.snapshotted_at.asc())
        .all()
    )

    return ComplianceTimelineResponse(
        ai_system_id=ai_system.id,
        ai_system_name=ai_system.name,
        snapshots=[ComplianceSnapshotResponse.model_validate(s) for s in snapshots],
    )


@router.get("/summary")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregate compliance stats for the current user's systems."""
    systems = db.query(AISystem).filter(AISystem.owner_id == current_user.id).all()

    by_risk_level = {level.value: 0 for level in RiskLevel}
    by_compliance_status = {value.value: 0 for value in ComplianceStatus}
    scores = []

    for system in systems:
        if system.risk_level:
            by_risk_level[system.risk_level.value] = by_risk_level.get(system.risk_level.value, 0) + 1
        status_value = (
            system.compliance_status.value
            if system.compliance_status
            else ComplianceStatus.NOT_STARTED.value
        )
        by_compliance_status[status_value] = by_compliance_status.get(status_value, 0) + 1
        if system.compliance_score is not None:
            scores.append(system.compliance_score)

    documents_generated = (
        db.query(Document).filter(Document.owner_id == current_user.id).count()
    )

    return {
        "total_systems": len(systems),
        "by_risk_level": by_risk_level,
        "by_compliance_status": by_compliance_status,
        "documents_generated": documents_generated,
        # compliance_score is stored on a 0–100 scale
        "average_compliance_score": round(sum(scores) / len(scores), 1) if scores else None,
    }
