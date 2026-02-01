"""Webhook API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.webhook import (
    WebhookCreate, WebhookUpdate, WebhookResponse, WebhookListResponse,
    WebhookDeliveryResponse, WebhookDeliveryListResponse,
    TestWebhookRequest, TestWebhookResponse,
    WebhookEventsListResponse
)
from ..services.webhook_service import WebhookService, WEBHOOK_EVENTS
from ..core.deps import CurrentUser, AdminUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    enabled_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all webhooks"""
    webhook_service = WebhookService(db)
    webhooks, total = webhook_service.list_webhooks(enabled_only, skip, limit)

    return WebhookListResponse(
        items=[WebhookResponse.model_validate(w) for w in webhooks],
        total=total
    )


@router.get("/events", response_model=WebhookEventsListResponse)
async def get_available_events(current_user: CurrentUser):
    """Get list of available webhook events"""
    return WebhookEventsListResponse(
        events=[
            {
                "event": e["event"],
                "description": e["description"],
                "example_payload": {
                    "event": e["event"],
                    "data": {"example": "data"},
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
            for e in WEBHOOK_EVENTS
        ]
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_WEBHOOKS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new webhook"""
    webhook_service = WebhookService(db)
    webhook = webhook_service.create_webhook(webhook_data, current_user.id)

    return WebhookResponse.model_validate(webhook)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get webhook by ID"""
    webhook_service = WebhookService(db)
    webhook = webhook_service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    return WebhookResponse.model_validate(webhook)


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_WEBHOOKS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a webhook"""
    webhook_service = WebhookService(db)
    webhook = webhook_service.update_webhook(webhook_id, webhook_data)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_WEBHOOKS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a webhook"""
    webhook_service = WebhookService(db)
    success = webhook_service.delete_webhook(webhook_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )


@router.post("/{webhook_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    webhook_id: int,
    test_data: TestWebhookRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_WEBHOOKS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Test a webhook"""
    webhook_service = WebhookService(db)
    result = await webhook_service.test_webhook(
        webhook_id,
        test_data.event_type,
        test_data.data
    )

    return TestWebhookResponse(**result)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def get_webhook_deliveries(
    webhook_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get delivery history for a webhook"""
    webhook_service = WebhookService(db)
    deliveries, total = webhook_service.get_deliveries(webhook_id, status, skip, limit)

    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total
    )


@router.post("/{webhook_id}/deliveries/{delivery_id}/resend")
async def resend_delivery(
    webhook_id: int,
    delivery_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_WEBHOOKS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Resend a failed delivery"""
    webhook_service = WebhookService(db)
    delivery = webhook_service.resend_delivery(delivery_id)

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )

    return {"message": "Delivery queued for resend"}


@router.get("/deliveries/recent", response_model=WebhookDeliveryListResponse)
async def get_recent_deliveries(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """Get recent deliveries across all webhooks"""
    webhook_service = WebhookService(db)
    deliveries, total = webhook_service.get_deliveries(
        webhook_id=None,
        status=status,
        limit=limit
    )

    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total
    )
