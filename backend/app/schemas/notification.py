"""Notification schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Channel schemas
class NotificationChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    channel_type: str = Field(..., pattern="^(email|slack|telegram|webhook|discord)$")
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    id: int
    verified: bool = False
    last_test: Optional[datetime] = None
    last_test_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class NotificationChannelListResponse(BaseModel):
    items: List[NotificationChannelResponse]
    total: int


# Rule schemas
class NotificationRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    channel_id: int
    event_types: List[str] = Field(default_factory=list)
    router_filter: Dict[str, Any] = Field(default_factory=dict)
    severity_filter: List[str] = Field(default_factory=list)

    cooldown_seconds: int = Field(default=300, ge=0)
    max_per_hour: int = Field(default=10, ge=1)
    aggregate: bool = False
    aggregate_window: int = Field(default=60, ge=1)

    custom_template: Optional[str] = None
    include_details: bool = True
    enabled: bool = True


class NotificationRuleCreate(NotificationRuleBase):
    pass


class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    event_types: Optional[List[str]] = None
    router_filter: Optional[Dict[str, Any]] = None
    severity_filter: Optional[List[str]] = None

    cooldown_seconds: Optional[int] = Field(None, ge=0)
    max_per_hour: Optional[int] = Field(None, ge=1)
    aggregate: Optional[bool] = None
    aggregate_window: Optional[int] = Field(None, ge=1)

    custom_template: Optional[str] = None
    include_details: Optional[bool] = None
    enabled: Optional[bool] = None


class NotificationRuleResponse(NotificationRuleBase):
    id: int
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationRuleListResponse(BaseModel):
    items: List[NotificationRuleResponse]
    total: int


# Log schemas
class NotificationLogResponse(BaseModel):
    id: int
    channel_id: int
    rule_id: Optional[int] = None
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    status: str
    error_message: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationLogListResponse(BaseModel):
    items: List[NotificationLogResponse]
    total: int


# Test notification
class TestNotificationRequest(BaseModel):
    message: Optional[str] = "This is a test notification from MikroTik Mass Updater"


class TestNotificationResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None
