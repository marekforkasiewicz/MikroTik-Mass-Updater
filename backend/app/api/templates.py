"""Configuration Templates API endpoints for Zero-Touch Provisioning"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse,
    TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateValidateRequest, TemplateValidateResponse,
    TemplateDeployRequest, TemplateDeployResponse, TemplateDeployRouterResult,
    ProfileCreate, ProfileUpdate, ProfileResponse, ProfileListResponse,
    DeploymentResponse, DeploymentListResponse
)
from ..services.template_service import TemplateService
from ..core.deps import CurrentUser, OperatorUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/templates", tags=["Templates"])


# ==================== Template List & Create ====================

@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags")
):
    """List all configuration templates"""
    service = TemplateService(db)
    tag_list = tags.split(",") if tags else None
    templates, total = service.list_templates(skip, limit, category, is_active, tag_list)

    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in templates],
        total=total
    )


@router.get("/categories", response_model=List[str])
async def get_template_categories(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get list of template categories"""
    service = TemplateService(db)
    return service.get_categories()


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new configuration template"""
    service = TemplateService(db)

    # Check for existing name
    if service.get_template_by_name(data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )

    try:
        template = service.create_template(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return TemplateResponse.model_validate(template)


# ==================== Template Validation (static path - must be before /{template_id}) ====================

@router.post("/validate", response_model=TemplateValidateResponse)
async def validate_template_syntax(
    data: TemplateValidateRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Validate template syntax without saving"""
    service = TemplateService(db)
    valid, errors, warnings = service.validate_template(data.content)

    return TemplateValidateResponse(
        valid=valid,
        errors=errors,
        warnings=warnings
    )


# ==================== Device Profiles (static paths - must be before /{template_id}) ====================

@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None)
):
    """List all device profiles"""
    service = TemplateService(db)
    profiles, total = service.list_profiles(skip, limit, is_active)

    items = []
    for profile in profiles:
        response = ProfileResponse.model_validate(profile)
        response.template_ids = [t.id for t in profile.templates]
        items.append(response)

    return ProfileListResponse(items=items, total=total)


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new device profile"""
    service = TemplateService(db)

    # Check for existing name
    if service.get_profile_by_name(data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile with this name already exists"
        )

    profile = service.create_profile(data)
    response = ProfileResponse.model_validate(profile)
    response.template_ids = [t.id for t in profile.templates]
    return response


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a device profile by ID"""
    service = TemplateService(db)
    profile = service.get_profile(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    response = ProfileResponse.model_validate(profile)
    response.template_ids = [t.id for t in profile.templates]
    return response


@router.put("/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a device profile"""
    service = TemplateService(db)

    # Check name uniqueness if changing
    if data.name:
        existing = service.get_profile_by_name(data.name)
        if existing and existing.id != profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile with this name already exists"
            )

    profile = service.update_profile(profile_id, data)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    response = ProfileResponse.model_validate(profile)
    response.template_ids = [t.id for t in profile.templates]
    return response


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a device profile"""
    service = TemplateService(db)
    success = service.delete_profile(profile_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )


@router.get("/profiles/{profile_id}/routers")
async def get_profile_matching_routers(
    profile_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get routers that match a profile's device filter"""
    service = TemplateService(db)
    routers = service.get_routers_for_profile(profile_id)

    return {
        "profile_id": profile_id,
        "routers": [
            {
                "id": r.id,
                "ip": r.ip,
                "identity": r.identity,
                "model": r.model,
                "architecture": r.architecture,
                "is_online": r.is_online
            }
            for r in routers
        ],
        "total": len(routers)
    }


# ==================== Deployment History (static paths - must be before /{template_id}) ====================

@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)],
    template_id: Optional[int] = Query(None),
    router_id: Optional[int] = Query(None),
    deployment_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List template deployments"""
    service = TemplateService(db)
    deployments, total = service.list_deployments(
        template_id=template_id,
        router_id=router_id,
        status=deployment_status,
        skip=skip,
        limit=limit
    )

    return DeploymentListResponse(
        items=[DeploymentResponse.model_validate(d) for d in deployments],
        total=total
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a deployment by ID"""
    service = TemplateService(db)
    deployment = service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    return DeploymentResponse.model_validate(deployment)


# ==================== Template CRUD by ID (parameterized paths - must be AFTER static paths) ====================

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a template by ID"""
    service = TemplateService(db)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a configuration template"""
    service = TemplateService(db)

    # Check name uniqueness if changing
    if data.name:
        existing = service.get_template_by_name(data.name)
        if existing and existing.id != template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template with this name already exists"
            )

    try:
        template = service.update_template(template_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a configuration template"""
    service = TemplateService(db)
    success = service.delete_template(template_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )


@router.post("/{template_id}/validate", response_model=TemplateValidateResponse)
async def validate_existing_template(
    template_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Validate an existing template's syntax"""
    service = TemplateService(db)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    valid, errors, warnings = service.validate_template(template.content)

    return TemplateValidateResponse(
        valid=valid,
        errors=errors,
        warnings=warnings
    )


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: int,
    data: TemplatePreviewRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Preview rendered template with variables"""
    service = TemplateService(db)

    try:
        rendered, variables_used = service.preview_template(
            template_id,
            router_id=data.router_id,
            variables=data.variables
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return TemplatePreviewResponse(
        rendered=rendered,
        variables_used=variables_used
    )


@router.post("/{template_id}/deploy", response_model=TemplateDeployResponse)
async def deploy_template(
    template_id: int,
    data: TemplateDeployRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[None, Depends(require_permission(Permission.DEPLOY_TEMPLATES))],
    db: Annotated[Session, Depends(get_db)]
):
    """Deploy template to routers"""
    from ..models.router import Router
    from ..models.task import Task
    from ..core.enums import TaskType, TaskStatus
    from ..services.template_deploy_service import run_template_deploy_task
    from ..config import settings

    service = TemplateService(db)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    if not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deploy inactive template"
        )

    # Get routers
    routers = db.query(Router).filter(Router.id.in_(data.router_ids)).all()
    if not routers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid routers found"
        )

    # For dry_run, just return preview results without creating a task
    if data.dry_run:
        results = []
        for router in routers:
            result = TemplateDeployRouterResult(
                router_id=router.id,
                router_ip=router.ip,
                router_identity=router.identity,
                status="dry_run"
            )
            try:
                rendered = service.render_template_for_router(template, router, data.variables)
                result.rendered_content = rendered
            except ValueError as e:
                result.status = "failed"
                result.error = str(e)
            results.append(result)

        return TemplateDeployResponse(
            template_id=template_id,
            total_routers=len(routers),
            dry_run=True,
            results=results
        )

    # Create a task for actual deployment
    task = Task(
        type=TaskType.TEMPLATE_DEPLOY.value,
        status=TaskStatus.PENDING.value,
        config={
            "template_id": template_id,
            "template_name": template.name,
            "router_ids": data.router_ids,
            "variables": data.variables,
            "backup_before": data.backup_before
        },
        total=len(routers)
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Start background task
    background_tasks.add_task(
        run_template_deploy_task,
        task.id,
        task.config,
        str(settings.DATABASE_URL)
    )

    # Return immediate response with task ID
    return TemplateDeployResponse(
        deployment_id=None,
        template_id=template_id,
        total_routers=len(routers),
        dry_run=False,
        results=[
            TemplateDeployRouterResult(
                router_id=r.id,
                router_ip=r.ip,
                router_identity=r.identity,
                status="pending"
            )
            for r in routers
        ],
        task_id=task.id  # Include task ID for tracking
    )
