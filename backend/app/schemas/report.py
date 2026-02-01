"""Report schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReportFilter(BaseModel):
    router_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None
    tags: Optional[List[str]] = None
    status: Optional[List[str]] = None  # online, offline, needs_update
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(inventory|updates|health|activity|backups|custom)$")
    title: Optional[str] = None
    format: str = Field(default="pdf", pattern="^(pdf|excel|csv|json)$")
    filters: ReportFilter = Field(default_factory=ReportFilter)
    include_charts: bool = True
    include_details: bool = True
    sections: Optional[List[str]] = None  # For custom reports


class ReportResponse(BaseModel):
    id: str
    report_type: str
    title: str
    format: str
    status: str  # pending, generating, completed, failed
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_by: Optional[int] = None


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int


# Inventory report data
class RouterInventoryItem(BaseModel):
    id: int
    ip: str
    identity: Optional[str] = None
    model: Optional[str] = None
    ros_version: Optional[str] = None
    firmware: Optional[str] = None
    update_channel: Optional[str] = None
    is_online: bool = False
    has_updates: bool = False
    location: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    uptime: Optional[str] = None
    last_seen: Optional[datetime] = None


class InventoryReportData(BaseModel):
    generated_at: datetime
    total_routers: int
    online_count: int
    offline_count: int
    needs_update_count: int
    routers: List[RouterInventoryItem]
    version_summary: Dict[str, int]
    model_summary: Dict[str, int]


# Update history report
class UpdateHistoryItem(BaseModel):
    router_id: int
    router_identity: Optional[str] = None
    router_ip: str
    update_type: str
    from_version: Optional[str] = None
    to_version: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class UpdateReportData(BaseModel):
    generated_at: datetime
    date_range_start: datetime
    date_range_end: datetime
    total_updates: int
    successful_updates: int
    failed_updates: int
    updates: List[UpdateHistoryItem]


# Health report
class HealthReportItem(BaseModel):
    router_id: int
    router_identity: Optional[str] = None
    router_ip: str
    status: str  # healthy, warning, critical
    uptime_percentage: float
    avg_latency_ms: Optional[float] = None
    alerts_count: int
    issues: List[str] = Field(default_factory=list)


class HealthReportData(BaseModel):
    generated_at: datetime
    date_range_start: datetime
    date_range_end: datetime
    total_routers: int
    healthy_count: int
    warning_count: int
    critical_count: int
    avg_uptime_percentage: float
    routers: List[HealthReportItem]


# Quick export response
class QuickExportResponse(BaseModel):
    content: str  # For CSV/JSON inline content
    filename: str
    content_type: str
