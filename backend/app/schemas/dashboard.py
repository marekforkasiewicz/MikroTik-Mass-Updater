"""Dashboard schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RouterStats(BaseModel):
    total: int = 0
    online: int = 0
    offline: int = 0
    needs_update: int = 0
    firmware_update: int = 0


class VersionDistribution(BaseModel):
    version: str
    count: int
    percentage: float


class ModelDistribution(BaseModel):
    model: str
    count: int
    percentage: float


class UpdateChannelDistribution(BaseModel):
    channel: str
    count: int
    percentage: float


class HealthSummary(BaseModel):
    healthy: int = 0
    warning: int = 0
    critical: int = 0
    unknown: int = 0


class RecentActivity(BaseModel):
    id: str | int
    type: str  # scan, update, backup, script, alert
    title: str
    description: Optional[str] = None
    status: str
    router_id: Optional[int] = None
    router_identity: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    created_at: datetime


class ScheduleStatus(BaseModel):
    id: int
    name: str
    task_type: str
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_status: Optional[str] = None


class AlertSummary(BaseModel):
    active_alerts: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0
    info_alerts: int = 0
    recent_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class SystemStatus(BaseModel):
    scheduler_running: bool = False
    monitoring_active: bool = False
    websocket_connections: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0


class DashboardResponse(BaseModel):
    router_stats: RouterStats
    version_distribution: List[VersionDistribution]
    model_distribution: List[ModelDistribution]
    channel_distribution: List[UpdateChannelDistribution]
    health_summary: HealthSummary
    recent_activity: List[RecentActivity]
    upcoming_schedules: List[ScheduleStatus]
    alert_summary: AlertSummary
    system_status: SystemStatus


class UptimeHistoryEntry(BaseModel):
    router_id: int
    identity: Optional[str] = None
    timestamp: datetime
    is_online: bool
    latency_ms: Optional[float] = None


class UptimeHistoryResponse(BaseModel):
    router_id: int
    entries: List[UptimeHistoryEntry]
    uptime_percentage: float
    start_time: datetime
    end_time: datetime


class ChartDataPoint(BaseModel):
    label: str
    value: float
    color: Optional[str] = None


class ChartResponse(BaseModel):
    chart_type: str  # pie, bar, line, doughnut
    title: str
    data: List[ChartDataPoint]
    labels: List[str] = Field(default_factory=list)


class TimeSeriesDataPoint(BaseModel):
    timestamp: datetime
    value: float


class TimeSeriesResponse(BaseModel):
    metric: str
    router_id: Optional[int] = None
    data: List[TimeSeriesDataPoint]
    start_time: datetime
    end_time: datetime
