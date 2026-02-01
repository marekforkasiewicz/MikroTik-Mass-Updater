"""Schedule schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    task_type: str = Field(..., pattern="^(scan|quick_scan|update|backup|script|health_check)$")
    config: Dict[str, Any] = Field(default_factory=dict)

    target_type: str = Field(default="all", pattern="^(all|group|specific)$")
    target_ids: List[int] = Field(default_factory=list)

    cron_expression: Optional[str] = None
    timezone: str = Field(default="UTC")
    interval_seconds: Optional[int] = Field(None, ge=60)

    enabled: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=0)
    timeout: int = Field(default=3600, ge=60)

    run_on_startup: bool = False
    run_if_missed: bool = True


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, pattern="^(scan|quick_scan|update|backup|script|health_check)$")
    config: Optional[Dict[str, Any]] = None

    target_type: Optional[str] = Field(None, pattern="^(all|group|specific)$")
    target_ids: Optional[List[int]] = None

    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    interval_seconds: Optional[int] = Field(None, ge=60)

    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay: Optional[int] = Field(None, ge=0)
    timeout: Optional[int] = Field(None, ge=60)

    run_on_startup: Optional[bool] = None
    run_if_missed: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    id: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = 0
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    items: List[ScheduleResponse]
    total: int


class ScheduleExecutionResponse(BaseModel):
    id: int
    schedule_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    routers_affected: int = 0
    routers_success: int = 0
    routers_failed: int = 0
    trigger_type: str = "scheduled"
    triggered_by: Optional[int] = None

    class Config:
        from_attributes = True


class ScheduleExecutionListResponse(BaseModel):
    items: List[ScheduleExecutionResponse]
    total: int


class RunScheduleNowRequest(BaseModel):
    """Request to run a schedule immediately"""
    pass  # No additional fields needed


class CronDescriptionResponse(BaseModel):
    """Response for human-readable cron description"""
    cron: str
    description: str
    next_runs: List[datetime]
