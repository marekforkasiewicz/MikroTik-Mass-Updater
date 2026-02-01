"""Compliance API endpoints for configuration compliance checking"""

from typing import Annotated, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.router import Router
from ..schemas.compliance import (
    BaselineCreate, BaselineUpdate, BaselineResponse, BaselineListResponse,
    ComplianceCheckRequest, ComplianceCheckResponse, ComplianceCheckDetailResponse,
    ComplianceCheckListResponse, ComplianceSummaryResponse,
    ConfigExportResponse, ConfigDiffRequest, ConfigDiffResponse
)
from ..services.compliance_service import ComplianceService
from ..core.deps import require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/compliance", tags=["Compliance"])


# ==================== Config Export ====================

@router.get("/routers/{router_id}/export", response_model=ConfigExportResponse)
async def export_router_config(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_ROUTERS))],
    db: Annotated[Session, Depends(get_db)],
    hide_sensitive: bool = Query(True, description="Hide sensitive data")
):
    """Export router configuration"""
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router not found"
        )

    service = ComplianceService(db)
    config, error = service.export_router_config(router_id, hide_sensitive)

    return ConfigExportResponse(
        router_id=router.id,
        router_ip=router.ip,
        router_identity=router.identity,
        config=config,
        error=error
    )


# ==================== Config Diff ====================

@router.post("/diff", response_model=ConfigDiffResponse)
async def diff_configs(
    data: ConfigDiffRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_ROUTERS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Compare two configurations"""
    service = ComplianceService(db)

    # If router IDs provided, export and compare
    if data.router_a_id and data.router_b_id:
        result = service.diff_routers(
            data.router_a_id,
            data.router_b_id,
            data.hide_sensitive
        )
        if "error" in result:
            return ConfigDiffResponse(
                unified_diff="",
                added_lines=0,
                removed_lines=0,
                has_changes=False,
                label_a=data.label_a,
                label_b=data.label_b,
                error=result["error"]
            )
        return ConfigDiffResponse(**result)

    # If configs provided directly, compare them
    if data.config_a and data.config_b:
        result = service.diff_configs(
            data.config_a,
            data.config_b,
            data.label_a,
            data.label_b
        )
        return ConfigDiffResponse(**result)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either router_a_id+router_b_id or config_a+config_b must be provided"
    )


# ==================== Baselines ====================

@router.get("/baselines", response_model=BaselineListResponse)
async def list_baselines(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None)
):
    """List all compliance baselines"""
    service = ComplianceService(db)
    baselines, total = service.list_baselines(skip, limit, is_active)

    return BaselineListResponse(
        items=[BaselineResponse.model_validate(b) for b in baselines],
        total=total
    )


@router.post("/baselines", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED)
async def create_baseline(
    data: BaselineCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new compliance baseline"""
    service = ComplianceService(db)

    # Check for existing name
    if service.get_baseline_by_name(data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baseline with this name already exists"
        )

    # Convert rules to dict
    rules = [r.model_dump() for r in data.rules]

    baseline = service.create_baseline(
        name=data.name,
        description=data.description,
        rules=rules,
        tags=data.tags
    )

    return BaselineResponse.model_validate(baseline)


@router.get("/baselines/{baseline_id}", response_model=BaselineResponse)
async def get_baseline(
    baseline_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a baseline by ID"""
    service = ComplianceService(db)
    baseline = service.get_baseline(baseline_id)

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline not found"
        )

    return BaselineResponse.model_validate(baseline)


@router.put("/baselines/{baseline_id}", response_model=BaselineResponse)
async def update_baseline(
    baseline_id: int,
    data: BaselineUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a compliance baseline"""
    service = ComplianceService(db)

    # Check name uniqueness if changing
    if data.name:
        existing = service.get_baseline_by_name(data.name)
        if existing and existing.id != baseline_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Baseline with this name already exists"
            )

    update_data = data.model_dump(exclude_unset=True)

    # Convert rules to dict if provided
    if 'rules' in update_data and update_data['rules'] is not None:
        update_data['rules'] = [
            r.model_dump() if hasattr(r, 'model_dump') else r
            for r in update_data['rules']
        ]

    baseline = service.update_baseline(baseline_id, **update_data)

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline not found"
        )

    return BaselineResponse.model_validate(baseline)


@router.delete("/baselines/{baseline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_baseline(
    baseline_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a compliance baseline"""
    service = ComplianceService(db)
    success = service.delete_baseline(baseline_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline not found"
        )


# ==================== Compliance Checks ====================

@router.post("/check", response_model=list[ComplianceCheckResponse])
async def run_compliance_check(
    data: ComplianceCheckRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Run compliance check for routers against a baseline"""
    service = ComplianceService(db)

    # Verify baseline exists
    baseline = service.get_baseline(data.baseline_id)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline not found"
        )

    # Verify routers exist
    routers = db.query(Router).filter(Router.id.in_(data.router_ids)).all()
    if len(routers) != len(data.router_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some routers not found"
        )

    checks = service.bulk_check_compliance(data.router_ids, data.baseline_id)

    return [ComplianceCheckResponse.model_validate(c) for c in checks]


@router.get("/checks", response_model=ComplianceCheckListResponse)
async def list_compliance_checks(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    baseline_id: Optional[int] = Query(None),
    check_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List compliance checks with optional filters"""
    service = ComplianceService(db)
    checks, total = service.list_checks(
        router_id=router_id,
        baseline_id=baseline_id,
        status=check_status,
        skip=skip,
        limit=limit
    )

    return ComplianceCheckListResponse(
        items=[ComplianceCheckResponse.model_validate(c) for c in checks],
        total=total
    )


@router.get("/checks/{check_id}", response_model=ComplianceCheckDetailResponse)
async def get_compliance_check(
    check_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a compliance check by ID with full details"""
    service = ComplianceService(db)
    check = service.get_check(check_id)

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance check not found"
        )

    return ComplianceCheckDetailResponse.model_validate(check)


@router.get("/summary", response_model=ComplianceSummaryResponse)
async def get_compliance_summary(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    baseline_id: Optional[int] = Query(None)
):
    """Get compliance summary across all routers"""
    service = ComplianceService(db)
    summary = service.get_compliance_summary(baseline_id)

    return ComplianceSummaryResponse(**summary)
