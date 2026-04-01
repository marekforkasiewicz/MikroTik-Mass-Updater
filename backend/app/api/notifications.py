"""Notification API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.notification import (
    NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelResponse,
    NotificationChannelListResponse,
    NotificationRuleCreate, NotificationRuleUpdate, NotificationRuleResponse,
    NotificationRuleListResponse,
    NotificationLogResponse, NotificationLogListResponse,
    TestNotificationRequest, TestNotificationResponse
)
from ..services.notification_service import NotificationService
from ..core.deps import require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Channel endpoints
@router.get("/channels", response_model=NotificationChannelListResponse)
async def list_channels(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """List all notification channels"""
    notification_service = NotificationService(db)
    channels = notification_service.list_channels()

    return NotificationChannelListResponse(
        items=[NotificationChannelResponse.model_validate(c) for c in channels],
        total=len(channels)
    )


@router.post("/channels", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: NotificationChannelCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a notification channel"""
    notification_service = NotificationService(db)
    channel = notification_service.create_channel(channel_data, current_user.id)
    return NotificationChannelResponse.model_validate(channel)


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_channel(
    channel_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get channel by ID"""
    notification_service = NotificationService(db)
    channel = notification_service.get_channel(channel_id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    return NotificationChannelResponse.model_validate(channel)


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a channel"""
    notification_service = NotificationService(db)
    channel = notification_service.update_channel(channel_id, channel_data)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    return NotificationChannelResponse.model_validate(channel)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a channel"""
    notification_service = NotificationService(db)
    success = notification_service.delete_channel(channel_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )


@router.post("/channels/{channel_id}/test", response_model=TestNotificationResponse)
async def test_channel(
    channel_id: int,
    test_data: TestNotificationRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Test a notification channel"""
    notification_service = NotificationService(db)
    result = await notification_service.test_channel(channel_id, test_data.message)

    return TestNotificationResponse(**result)


# Rule endpoints
@router.get("/rules", response_model=NotificationRuleListResponse)
async def list_rules(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)],
    channel_id: Optional[int] = Query(None)
):
    """List notification rules"""
    notification_service = NotificationService(db)
    rules = notification_service.list_rules(channel_id)

    return NotificationRuleListResponse(
        items=[NotificationRuleResponse.model_validate(r) for r in rules],
        total=len(rules)
    )


@router.post("/rules", response_model=NotificationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: NotificationRuleCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a notification rule"""
    notification_service = NotificationService(db)

    # Verify channel exists
    channel = notification_service.get_channel(rule_data.channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel not found"
        )

    rule = notification_service.create_rule(rule_data)
    return NotificationRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: NotificationRuleUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a notification rule"""
    notification_service = NotificationService(db)
    rule = notification_service.update_rule(rule_id, rule_data)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )

    return NotificationRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a notification rule"""
    notification_service = NotificationService(db)
    success = notification_service.delete_rule(rule_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )


# Log endpoints
@router.get("/logs", response_model=NotificationLogListResponse)
async def get_notification_logs(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_NOTIFICATIONS))],
    db: Annotated[Session, Depends(get_db)],
    channel_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get notification delivery logs"""
    notification_service = NotificationService(db)
    logs = notification_service.get_logs(channel_id, status, limit)

    return NotificationLogListResponse(
        items=[NotificationLogResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


# Available event types
@router.get("/event-types")
async def get_event_types(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_NOTIFICATIONS))]
):
    """Get available event types for notification rules"""
    return {
        "event_types": [
            {"value": "router_offline", "label": "Router Offline"},
            {"value": "router_online", "label": "Router Online"},
            {"value": "update_available", "label": "Update Available"},
            {"value": "update_completed", "label": "Update Completed"},
            {"value": "update_failed", "label": "Update Failed"},
            {"value": "backup_completed", "label": "Backup Completed"},
            {"value": "backup_failed", "label": "Backup Failed"},
            {"value": "scan_completed", "label": "Scan Completed"},
            {"value": "script_executed", "label": "Script Executed"},
            {"value": "health_warning", "label": "Health Warning"},
            {"value": "health_critical", "label": "Health Critical"},
            {"value": "schedule_failed", "label": "Schedule Failed"},
        ]
    }
