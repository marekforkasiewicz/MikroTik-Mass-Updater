"""Monitoring API endpoints"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.router import Router
from ..schemas.monitoring import (
    MonitoringConfigCreate, MonitoringConfigUpdate, MonitoringConfigResponse,
    HealthCheckResponse, HealthCheckListResponse,
    AlertResponse, AlertListResponse,
    AcknowledgeAlertRequest, ResolveAlertRequest,
    MonitoringOverviewResponse
)
from ..services.monitoring_service import MonitoringService
from ..core.deps import OperatorUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/overview", response_model=MonitoringOverviewResponse)
async def get_monitoring_overview(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get monitoring overview for all routers"""
    monitoring_service = MonitoringService(db)
    overview = monitoring_service.get_monitoring_overview()
    return MonitoringOverviewResponse(**overview)


@router.get("/config", response_model=MonitoringConfigResponse)
async def get_global_config(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get global monitoring configuration"""
    monitoring_service = MonitoringService(db)
    config = monitoring_service.ensure_global_config()
    return MonitoringConfigResponse.model_validate(config)


@router.put("/config", response_model=MonitoringConfigResponse)
async def update_global_config(
    config_data: MonitoringConfigUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update global monitoring configuration"""
    monitoring_service = MonitoringService(db)
    global_config = monitoring_service.ensure_global_config()
    config = monitoring_service.update_config(global_config.id, config_data)
    return MonitoringConfigResponse.model_validate(config)


@router.get("/routers/{router_id}/config", response_model=MonitoringConfigResponse)
async def get_router_config(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get monitoring configuration for a router"""
    monitoring_service = MonitoringService(db)
    config = monitoring_service.get_config(router_id)

    if not config:
        # Return global config as default
        config = monitoring_service.ensure_global_config()

    return MonitoringConfigResponse.model_validate(config)


@router.post("/routers/{router_id}/config", response_model=MonitoringConfigResponse)
async def create_router_config(
    router_id: int,
    config_data: MonitoringConfigCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create custom monitoring configuration for a router"""
    # Verify router exists
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router not found"
        )

    config_data.router_id = router_id
    monitoring_service = MonitoringService(db)
    config = monitoring_service.create_config(config_data)
    return MonitoringConfigResponse.model_validate(config)


@router.post("/routers/{router_id}/check")
async def trigger_health_check(
    router_id: int,
    current_user: OperatorUser,
    db: Annotated[Session, Depends(get_db)],
    check_type: str = Query("full", pattern="^(ping|port|full)$")
):
    """Trigger a health check for a router"""
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router not found"
        )

    monitoring_service = MonitoringService(db)
    check = await monitoring_service.check_router(router, check_type)

    return HealthCheckResponse.model_validate(check)


@router.get("/routers/{router_id}/history", response_model=HealthCheckListResponse)
async def get_health_history(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)],
    check_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720)
):
    """Get health check history for a router"""
    monitoring_service = MonitoringService(db)
    checks = monitoring_service.get_health_history(router_id, check_type, hours)

    return HealthCheckListResponse(
        items=[HealthCheckResponse.model_validate(c) for c in checks],
        total=len(checks)
    )


# Alert endpoints
@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get alerts with filters"""
    monitoring_service = MonitoringService(db)
    alerts, total = monitoring_service.get_alerts(router_id, status, severity, skip, limit)

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total
    )


@router.get("/alerts/active")
async def get_active_alerts(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get all active (unresolved) alerts"""
    monitoring_service = MonitoringService(db)
    alerts, total = monitoring_service.get_alerts(status="active")

    return {
        "total": total,
        "critical": sum(1 for a in alerts if a.severity == "critical"),
        "warning": sum(1 for a in alerts if a.severity == "warning"),
        "info": sum(1 for a in alerts if a.severity == "info"),
        "alerts": [AlertResponse.model_validate(a) for a in alerts]
    }


@router.post("/alerts/acknowledge")
async def acknowledge_alerts(
    request: AcknowledgeAlertRequest,
    current_user: OperatorUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Acknowledge alerts"""
    monitoring_service = MonitoringService(db)
    count = monitoring_service.acknowledge_alerts(request.alert_ids, current_user.id)

    return {"acknowledged": count}


@router.post("/alerts/resolve")
async def resolve_alerts(
    request: ResolveAlertRequest,
    current_user: OperatorUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Resolve alerts"""
    monitoring_service = MonitoringService(db)
    count = monitoring_service.resolve_alerts(request.alert_ids)

    return {"resolved": count}


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_MONITORING))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get alert by ID"""
    monitoring_service = MonitoringService(db)
    alerts, _ = monitoring_service.get_alerts()
    alert = next((a for a in alerts if a.id == alert_id), None)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return AlertResponse.model_validate(alert)
