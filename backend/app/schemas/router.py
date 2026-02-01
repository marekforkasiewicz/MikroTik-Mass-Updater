"""Pydantic schemas for Router"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RouterBase(BaseModel):
    """Base router schema"""
    ip: str = Field(..., description="Router IP address")
    port: int = Field(default=8728, description="API port")
    username: Optional[str] = Field(None, description="API username")
    password: Optional[str] = Field(None, description="API password")


class RouterCreate(RouterBase):
    """Schema for creating a router"""
    pass


class RouterUpdate(BaseModel):
    """Schema for updating a router"""
    ip: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


class RouterResponse(RouterBase):
    """Schema for router response"""
    id: int
    identity: Optional[str] = None
    model: Optional[str] = None
    ros_version: Optional[str] = None
    firmware: Optional[str] = None
    upgrade_firmware: Optional[str] = None
    update_channel: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    uptime: Optional[str] = None
    is_online: bool = False
    has_updates: bool = False
    has_firmware_update: bool = False
    last_seen: Optional[datetime] = None
    last_scan: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RouterImport(BaseModel):
    """Schema for importing routers from file"""
    content: str = Field(..., description="Content of list.txt file")
    replace: bool = Field(default=False, description="Replace existing routers")


class RouterListResponse(BaseModel):
    """Response with list of routers"""
    routers: List[RouterResponse]
    total: int
    online: int
    offline: int
    needs_update: int


class QuickScanResult(BaseModel):
    """Result of a quick scan for a single router"""
    ip: str
    ping_ok: bool = False
    ping_ms: float = 0.0
    port_api_open: bool = False
    port_ssh_open: bool = False
    ros_version: Optional[str] = None
    identity: Optional[str] = None
    status: str = "unknown"
    has_credentials: bool = False


class FullScanResult(BaseModel):
    """Result of a full scan for a single router"""
    ip: str
    identity: Optional[str] = None
    model: Optional[str] = None
    ros_version: Optional[str] = None
    firmware: Optional[str] = None
    upgrade_firmware: Optional[str] = None
    update_channel: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    uptime: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
