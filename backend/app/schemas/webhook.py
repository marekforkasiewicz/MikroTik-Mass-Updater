"""Webhook schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class WebhookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    url: str = Field(..., max_length=500)
    method: str = Field(default="POST", pattern="^(POST|PUT)$")

    headers: Dict[str, str] = Field(default_factory=dict)
    auth_type: Optional[str] = Field(None, pattern="^(none|basic|bearer|custom)$")
    auth_config: Dict[str, Any] = Field(default_factory=dict)

    content_type: str = Field(default="application/json")
    payload_template: Optional[str] = None
    include_signature: bool = True

    events: List[str] = Field(default_factory=list)
    router_filter: Dict[str, Any] = Field(default_factory=dict)

    retry_count: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=0)
    timeout: int = Field(default=30, ge=1, le=300)

    enabled: bool = True


class WebhookCreate(WebhookBase):
    pass


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    url: Optional[str] = Field(None, max_length=500)
    method: Optional[str] = Field(None, pattern="^(POST|PUT)$")

    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = Field(None, pattern="^(none|basic|bearer|custom)$")
    auth_config: Optional[Dict[str, Any]] = None

    content_type: Optional[str] = None
    payload_template: Optional[str] = None
    include_signature: Optional[bool] = None

    events: Optional[List[str]] = None
    router_filter: Optional[Dict[str, Any]] = None

    retry_count: Optional[int] = Field(None, ge=0, le=10)
    retry_delay: Optional[int] = Field(None, ge=0)
    timeout: Optional[int] = Field(None, ge=1, le=300)

    enabled: Optional[bool] = None


class WebhookResponse(WebhookBase):
    id: int
    verified: bool = False
    last_triggered: Optional[datetime] = None
    last_status: Optional[str] = None
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    items: List[WebhookResponse]
    total: int


# Delivery schemas
class WebhookDeliveryResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    request_url: str
    request_method: str
    request_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    response_body: Optional[str] = None
    status: str
    attempt_count: int = 1
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    next_retry_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    items: List[WebhookDeliveryResponse]
    total: int


# Test webhook
class TestWebhookRequest(BaseModel):
    event_type: str = "test"
    data: Dict[str, Any] = Field(default_factory=lambda: {"message": "Test webhook delivery"})


class TestWebhookResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


# Available events
class WebhookEventResponse(BaseModel):
    event: str
    description: str
    example_payload: Dict[str, Any]


class WebhookEventsListResponse(BaseModel):
    events: List[WebhookEventResponse]
