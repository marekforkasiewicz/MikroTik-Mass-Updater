"""Backup and rollback API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.backup import (
    BackupCreate, BackupResponse, BackupListResponse,
    RollbackCreate, RollbackResponse, RollbackListResponse,
    BulkBackupRequest, BulkBackupResponse
)
from ..services.rollback_service import RollbackService
from ..core.deps import CurrentUser, OperatorUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.get("", response_model=BackupListResponse)
async def list_backups(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    backup_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all backups"""
    rollback_service = RollbackService(db)
    backups, total = rollback_service.list_backups(router_id, backup_type, skip, limit)

    return BackupListResponse(
        items=[BackupResponse.model_validate(b) for b in backups],
        total=total
    )


@router.post("", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    backup_data: BackupCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.CREATE_BACKUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a backup for a router"""
    rollback_service = RollbackService(db)

    try:
        backup = rollback_service.create_backup(backup_data, current_user.id)
        return BackupResponse.model_validate(backup)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/bulk", response_model=BulkBackupResponse)
async def create_bulk_backup(
    request: BulkBackupRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.CREATE_BACKUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create backups for multiple routers"""
    from ..models.task import Task
    import uuid

    # Create a task for bulk backup
    task = Task(
        id=str(uuid.uuid4()),
        task_type="backup",
        status="pending",
        config={
            "router_ids": request.router_ids,
            "backup_type": request.backup_type,
            "includes_passwords": request.includes_passwords
        }
    )
    db.add(task)
    db.commit()

    # TODO: Trigger background task

    return BulkBackupResponse(
        task_id=task.id,
        message=f"Backup task created for {len(request.router_ids)} routers"
    )


@router.get("/{backup_id}", response_model=BackupResponse)
async def get_backup(
    backup_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get backup by ID"""
    rollback_service = RollbackService(db)
    backup = rollback_service.get_backup(backup_id)

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )

    return BackupResponse.model_validate(backup)


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.DELETE_BACKUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a backup"""
    rollback_service = RollbackService(db)
    success = rollback_service.delete_backup(backup_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Download a backup file"""
    rollback_service = RollbackService(db)
    backup = rollback_service.get_backup(backup_id)

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )

    if not backup.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup file not available"
        )

    import os
    if not os.path.exists(backup.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk"
        )

    return FileResponse(
        path=backup.file_path,
        filename=os.path.basename(backup.file_path),
        media_type="application/octet-stream"
    )


# Rollback endpoints
@router.post("/restore", response_model=RollbackResponse)
async def restore_backup(
    rollback_data: RollbackCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.RESTORE_BACKUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Restore a router from backup"""
    rollback_service = RollbackService(db)

    try:
        rollback = rollback_service.restore_backup(rollback_data, current_user.id)
        return RollbackResponse.model_validate(rollback)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/rollback-logs", response_model=RollbackListResponse)
async def list_rollback_logs(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
):
    """Get rollback history"""
    rollback_service = RollbackService(db)
    logs, total = rollback_service.get_rollback_logs(router_id, skip, limit)

    return RollbackListResponse(
        items=[RollbackResponse.model_validate(log) for log in logs],
        total=total
    )


@router.post("/cleanup")
async def cleanup_old_backups(
    current_user: Annotated[None, Depends(require_permission(Permission.DELETE_BACKUPS))],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(30, ge=1, le=365)
):
    """Clean up old backups"""
    rollback_service = RollbackService(db)
    rollback_service.cleanup_old_backups(days)

    return {"message": f"Cleaned up backups older than {days} days"}
