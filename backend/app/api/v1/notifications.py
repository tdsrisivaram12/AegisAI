"""
Notifications API — in-app event feed for users.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Endpoints:
  - GET    /notifications       — list notifications for the current user
  - POST   /notifications/read  — mark notifications as read
  - DELETE /notifications/{id}  — delete a single notification

Other modules can emit events with :func:`create_notification`.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationResponse, NotificationMarkRead

router = APIRouter()


def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    commit: bool = True,
) -> Notification:
    """Create and persist an in-app notification for ``user_id``."""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type.value
        if isinstance(notification_type, NotificationType)
        else str(notification_type),
        title=title,
        message=message,
        is_read=False,
        resource_type=resource_type,
        resource_id=resource_id,
        created_at=datetime.utcnow(),
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    return notification


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200, description="Maximum notifications to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's notifications, newest first."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    return query.order_by(desc(Notification.created_at)).limit(limit).all()


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    body: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark the given notification IDs as read (only the current user's own)."""
    if not body.ids:
        return None

    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.id.in_(body.ids),
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return None


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single notification owned by the current user."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    db.delete(notification)
    db.commit()
    return None
