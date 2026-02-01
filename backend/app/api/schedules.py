"""Schedule API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse,
    ScheduleExecutionResponse, ScheduleExecutionListResponse,
    CronDescriptionResponse
)
from ..services.scheduler_service import SchedulerService
from ..core.deps import CurrentUser, OperatorUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all scheduled tasks"""
    scheduler_service = SchedulerService(db)
    schedules, total = scheduler_service.list_schedules(skip, limit)

    return ScheduleListResponse(
        items=[ScheduleResponse.model_validate(s) for s in schedules],
        total=total
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new scheduled task"""
    # Validate cron or interval is provided
    if not schedule_data.cron_expression and not schedule_data.interval_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either cron_expression or interval_seconds must be provided"
        )

    scheduler_service = SchedulerService(db)

    try:
        schedule = scheduler_service.create_schedule(schedule_data, current_user.id)
        return ScheduleResponse.model_validate(schedule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/cron-describe")
async def describe_cron(
    current_user: CurrentUser,
    cron: str = Query(..., description="Cron expression to describe"),
    db: Annotated[Session, Depends(get_db)] = None
):
    """Get human-readable description of a cron expression"""
    scheduler_service = SchedulerService(db)
    result = scheduler_service.get_cron_description(cron)

    return CronDescriptionResponse(**result)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get scheduled task by ID"""
    scheduler_service = SchedulerService(db)
    schedule = scheduler_service.get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a scheduled task"""
    scheduler_service = SchedulerService(db)

    try:
        schedule = scheduler_service.update_schedule(schedule_id, schedule_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a scheduled task"""
    scheduler_service = SchedulerService(db)
    success = scheduler_service.delete_schedule(schedule_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )


@router.post("/{schedule_id}/enable", response_model=ScheduleResponse)
async def enable_schedule(
    schedule_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Enable a scheduled task"""
    scheduler_service = SchedulerService(db)
    schedule = scheduler_service.enable_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse.model_validate(schedule)


@router.post("/{schedule_id}/disable", response_model=ScheduleResponse)
async def disable_schedule(
    schedule_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Disable a scheduled task"""
    scheduler_service = SchedulerService(db)
    schedule = scheduler_service.disable_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse.model_validate(schedule)


@router.post("/{schedule_id}/run-now", response_model=ScheduleExecutionResponse)
async def run_schedule_now(
    schedule_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCHEDULES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Run a scheduled task immediately"""
    scheduler_service = SchedulerService(db)
    execution = scheduler_service.run_now(schedule_id, current_user.id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleExecutionResponse.model_validate(execution)


@router.get("/{schedule_id}/executions", response_model=ScheduleExecutionListResponse)
async def get_schedule_executions(
    schedule_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
):
    """Get execution history for a schedule"""
    scheduler_service = SchedulerService(db)
    executions, total = scheduler_service.get_executions(schedule_id, skip, limit)

    return ScheduleExecutionListResponse(
        items=[ScheduleExecutionResponse.model_validate(e) for e in executions],
        total=total
    )
