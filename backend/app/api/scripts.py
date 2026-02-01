"""Custom scripts API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.script import (
    ScriptCreate, ScriptUpdate, ScriptResponse, ScriptListResponse,
    ScriptExecuteRequest, ScriptExecutionResponse, ScriptExecutionListResponse,
    BulkScriptExecuteRequest, BulkScriptExecuteResponse,
    ValidateScriptRequest, ValidateScriptResponse
)
from ..services.script_service import ScriptService
from ..core.deps import CurrentUser, OperatorUser, require_permission
from ..core.permissions import Permission, Role

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.get("", response_model=ScriptListResponse)
async def list_scripts(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    category: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all custom scripts"""
    script_service = ScriptService(db)
    scripts, total = script_service.list_scripts(category, enabled_only, skip, limit)

    # Filter by allowed roles
    filtered = [
        s for s in scripts
        if current_user.role in (s.allowed_roles or ["admin", "operator"])
    ]

    return ScriptListResponse(
        items=[ScriptResponse.model_validate(s) for s in filtered],
        total=len(filtered)
    )


@router.get("/categories")
async def get_script_categories(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get list of script categories"""
    script_service = ScriptService(db)
    categories = script_service.get_categories()

    return {"categories": categories}


@router.post("", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def create_script(
    script_data: ScriptCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCRIPTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new custom script"""
    script_service = ScriptService(db)

    # Check for existing name
    if script_service.get_script_by_name(script_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script with this name already exists"
        )

    script = script_service.create_script(script_data, current_user.id)
    return ScriptResponse.model_validate(script)


@router.post("/validate", response_model=ValidateScriptResponse)
async def validate_script(
    request: ValidateScriptRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Validate script syntax"""
    script_service = ScriptService(db)
    result = script_service.validate_script(request.content, request.script_type)

    return ValidateScriptResponse(**result)


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get script by ID"""
    script_service = ScriptService(db)
    script = script_service.get_script(script_id)

    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )

    # Check role access
    if current_user.role not in (script.allowed_roles or ["admin", "operator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this script"
        )

    return ScriptResponse.model_validate(script)


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCRIPTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a script"""
    script_service = ScriptService(db)

    # Check name uniqueness if changing
    if script_data.name:
        existing = script_service.get_script_by_name(script_data.name)
        if existing and existing.id != script_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Script with this name already exists"
            )

    script = script_service.update_script(script_id, script_data, current_user.id)

    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )

    return ScriptResponse.model_validate(script)


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_SCRIPTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a script"""
    script_service = ScriptService(db)
    success = script_service.delete_script(script_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )


@router.post("/{script_id}/execute", response_model=ScriptExecutionResponse)
async def execute_script(
    script_id: int,
    request: ScriptExecuteRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.EXECUTE_SCRIPTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Execute a script on routers"""
    script_service = ScriptService(db)

    # Check script exists and user has access
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )

    if current_user.role not in (script.allowed_roles or ["admin", "operator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to execute this script"
        )

    if script.dangerous and current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can execute dangerous scripts"
        )

    # Execute on first router (for single execution)
    if len(request.router_ids) == 1:
        try:
            execution = script_service.execute_script(
                script_id=script_id,
                router_id=request.router_ids[0],
                variables=request.variables,
                user_id=current_user.id,
                dry_run=request.dry_run
            )
            return ScriptExecutionResponse.model_validate(execution)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # For multiple routers, create a bulk task
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Use /bulk-execute for multiple routers"
    )


@router.post("/{script_id}/bulk-execute", response_model=BulkScriptExecuteResponse)
async def bulk_execute_script(
    script_id: int,
    request: BulkScriptExecuteRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.EXECUTE_SCRIPTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Execute a script on multiple routers"""
    from ..models.task import Task
    import uuid

    script_service = ScriptService(db)

    # Check script exists
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )

    # Create task
    task = Task(
        id=str(uuid.uuid4()),
        type="script",
        status="pending",
        config={
            "script_id": script_id,
            "router_ids": request.router_ids,
            "variables": request.variables
        }
    )
    db.add(task)
    db.commit()

    return BulkScriptExecuteResponse(
        task_id=task.id,
        message=f"Script execution queued for {len(request.router_ids)} routers"
    )


@router.get("/{script_id}/executions", response_model=ScriptExecutionListResponse)
async def get_script_executions(
    script_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    router_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get execution history for a script"""
    script_service = ScriptService(db)
    executions, total = script_service.get_executions(
        script_id=script_id,
        router_id=router_id,
        status=status,
        skip=skip,
        limit=limit
    )

    return ScriptExecutionListResponse(
        items=[ScriptExecutionResponse.model_validate(e) for e in executions],
        total=total
    )
