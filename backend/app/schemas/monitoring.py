"""Monitoring schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Config schemas
class MonitoringConfigBase(BaseModel):
    ping_interval: int = Field(default=60, ge=10)
    port_check_interval: int = Field(default=300, ge=60)
    full_health_interval: int = Field(default=900, ge=300)

    ping_timeout: float = Field(default=2.0, ge=0.1, le=30.0)
    ping_warning_latency: float = Field(default=100.0, ge=1.0)
    ping_critical_latency: float = Field(default=500.0, ge=1.0)

    cpu_warning_percent: float = Field(default=80.0, ge=0, le=100)
    cpu_critical_percent: float = Field(default=95.0, ge=0, le=100)
    memory_warning_percent: float = Field(default=80.0, ge=0, le=100)
    memory_critical_percent: float = Field(default=95.0, ge=0, le=100)
    disk_warning_percent: float = Field(default=80.0, ge=0, le=100)
    disk_critical_percent: float = Field(default=95.0, ge=0, le=100)

    check_ping: bool = True
    check_api_port: bool = True
    check_ssh_port: bool = False
    check_resources: bool = True
    check_updates: bool = True

    alert_on_offline: bool = True
    alert_on_online: bool = True
    offline_threshold: int = Field(default=3, ge=1, le=10)

    enabled: bool = True


class MonitoringConfigCreate(MonitoringConfigBase):
    router_id: Optional[int] = None  # None means global config


class MonitoringConfigUpdate(BaseModel):
    ping_interval: Optional[int] = Field(None, ge=10)
    port_check_interval: Optional[int] = Field(None, ge=60)
    full_health_interval: Optional[int] = Field(None, ge=300)

    ping_timeout: Optional[float] = Field(None, ge=0.1, le=30.0)
    ping_warning_latency: Optional[float] = Field(None, ge=1.0)
    ping_critical_latency: Optional[float] = Field(None, ge=1.0)

    cpu_warning_percent: Optional[float] = Field(None, ge=0, le=100)
    cpu_critical_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_warning_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_critical_percent: Optional[float] = Field(None, ge=0, le=100)
    disk_warning_percent: Optional[float] = Field(None, ge=0, le=100)
    disk_critical_percent: Optional[float] = Field(None, ge=0, le=100)

    check_ping: Optional[bool] = None
    check_api_port: Optional[bool] = None
    check_ssh_port: Optional[bool] = None
    check_resources: Optional[bool] = None
    check_updates: Optional[bool] = None

    alert_on_offline: Optional[bool] = None
    alert_on_online: Optional[bool] = None
    offline_threshold: Optional[int] = Field(None, ge=1, le=10)

    enabled: Optional[bool] = None


class MonitoringConfigResponse(MonitoringConfigBase):
    id: int
    router_id: Optional[int] = None
    is_global: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Health check schemas
class HealthCheckResponse(BaseModel):
    id: int
    router_id: int
    check_type: str
    checked_at: datetime
    status: str
    is_online: Optional[bool] = None
    latency_ms: Optional[float] = None
    api_port_open: Optional[bool] = None
    ssh_port_open: Optional[bool] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    uptime_seconds: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class HealthCheckListResponse(BaseModel):
    items: List[HealthCheckResponse]
    total: int


# Alert schemas
class AlertResponse(BaseModel):
    id: int
    router_id: Optional[int] = None
    alert_type: str
    severity: str
    title: str
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: List[AlertResponse]
    total: int


class AcknowledgeAlertRequest(BaseModel):
    alert_ids: List[int]


class ResolveAlertRequest(BaseModel):
    alert_ids: List[int]


# Monitoring status overview
class RouterMonitoringStatus(BaseModel):
    router_id: int
    identity: Optional[str] = None
    ip: str
    status: str  # ok, warning, critical, unknown, offline
    is_online: bool
    latency_ms: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    memory_total_mb: Optional[int] = None
    architecture: Optional[str] = None
    disk_usage: Optional[float] = None
    uptime: Optional[str] = None
    last_check: Optional[datetime] = None
    active_alerts: int = 0


class MonitoringOverviewResponse(BaseModel):
    total_routers: int
    online_routers: int
    offline_routers: int
    warning_routers: int
    critical_routers: int
    active_alerts: int
    routers: List[RouterMonitoringStatus]
