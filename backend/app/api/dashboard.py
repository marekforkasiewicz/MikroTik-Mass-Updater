"""Dashboard API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.dashboard import (
    DashboardResponse, ChartResponse, TimeSeriesResponse,
    UptimeHistoryResponse
)
from ..services.dashboard_service import DashboardService
from ..core.deps import require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get complete dashboard data"""
    dashboard_service = DashboardService(db)
    data = dashboard_service.get_dashboard_data()

    return DashboardResponse(**data)


@router.get("/stats")
async def get_stats(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get quick stats overview"""
    dashboard_service = DashboardService(db)

    return {
        "router_stats": dashboard_service._get_router_stats(),
        "health_summary": dashboard_service._get_health_summary(),
        "alert_summary": dashboard_service._get_alert_summary()
    }


@router.get("/charts/{chart_type}", response_model=ChartResponse)
async def get_chart(
    chart_type: str,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get data for a specific chart"""
    valid_types = ["version_pie", "model_bar", "status_doughnut", "health_pie"]
    if chart_type not in valid_types:
        chart_type = "version_pie"

    dashboard_service = DashboardService(db)
    data = dashboard_service.get_chart_data(chart_type)

    return ChartResponse(**data)


@router.get("/time-series/{metric}", response_model=TimeSeriesResponse)
async def get_time_series(
    metric: str,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    hours: int = Query(24, ge=1, le=168)
):
    """Get time series data for a metric"""
    valid_metrics = ["latency", "cpu", "memory", "disk"]
    if metric not in valid_metrics:
        metric = "latency"

    dashboard_service = DashboardService(db)
    data = dashboard_service.get_time_series(metric, router_id, hours)

    return TimeSeriesResponse(**data)


@router.get("/uptime/{router_id}", response_model=UptimeHistoryResponse)
async def get_uptime_history(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)],
    hours: int = Query(24, ge=1, le=720)
):
    """Get uptime history for a router"""
    dashboard_service = DashboardService(db)
    data = dashboard_service.get_uptime_history(router_id, hours)

    return UptimeHistoryResponse(**data)


@router.get("/activity")
async def get_recent_activity(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50)
):
    """Get recent activity feed"""
    dashboard_service = DashboardService(db)
    activity = dashboard_service._get_recent_activity(limit)

    return {"activity": activity}


@router.get("/schedules")
async def get_upcoming_schedules(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(5, ge=1, le=20)
):
    """Get upcoming scheduled tasks"""
    dashboard_service = DashboardService(db)
    schedules = dashboard_service._get_upcoming_schedules(limit)

    return {"schedules": schedules}


@router.get("/system-status")
async def get_system_status(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get system status"""
    dashboard_service = DashboardService(db)
    status = dashboard_service._get_system_status()

    return status
