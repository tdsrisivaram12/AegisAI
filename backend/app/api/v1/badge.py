"""
Public Compliance Badge API — no authentication required.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

GET /badge/{system_id} returns an SVG badge (default) or JSON metadata so
organisations can embed the AI system's compliance status in a README or
website. The endpoint is public — callers need no JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_system import AISystem
from app.modules.badge.badge_generator import generate_badge_svg

router = APIRouter()


@router.get("/{system_id}", tags=["Compliance Badge"])
def get_compliance_badge(
    system_id: int,
    format: str = "svg",      # "svg" | "json"
    db: Session = Depends(get_db),
):
    """Return a public compliance badge for an AI system."""
    ai_system = db.query(AISystem).filter(AISystem.id == system_id).first()

    if not ai_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    risk_level = ai_system.risk_level.value if ai_system.risk_level else None
    compliance_status = (
        ai_system.compliance_status.value if ai_system.compliance_status else "not_started"
    )

    if format.lower() == "json":
        return {
            "system_id": ai_system.id,
            "system_name": ai_system.name,
            "risk_level": risk_level,
            "compliance_status": compliance_status,
            "compliance_score": ai_system.compliance_score,
        }

    svg = generate_badge_svg(ai_system.name, risk_level, compliance_status)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=60"},
    )
