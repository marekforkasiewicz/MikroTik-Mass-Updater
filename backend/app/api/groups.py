"""Router groups API endpoints"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse, GroupListResponse,
    GroupTreeResponse, GroupWithRoutersResponse,
    AddRoutersToGroupRequest, RemoveRoutersFromGroupRequest
)
from ..services.group_service import GroupService
from ..core.deps import require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("", response_model=GroupListResponse)
async def list_groups(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_GROUPS))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all router groups"""
    group_service = GroupService(db)
    groups, total = group_service.list_groups(skip, limit)

    items = []
    for group in groups:
        response = GroupResponse.model_validate(group)
        response.router_count = group_service.get_group_router_count(group.id)
        items.append(response)

    return GroupListResponse(items=items, total=total)


@router.get("/tree", response_model=List[GroupTreeResponse])
async def get_group_tree(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get groups in tree structure"""
    group_service = GroupService(db)
    root_groups = group_service.get_group_tree()

    def build_tree(group) -> GroupTreeResponse:
        response = GroupTreeResponse.model_validate(group)
        response.router_count = group_service.get_group_router_count(group.id)
        response.children = [build_tree(child) for child in group.children]
        return response

    return [build_tree(g) for g in root_groups]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new router group"""
    group_service = GroupService(db)

    # Check for existing name
    if group_service.get_group_by_name(group_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    # Validate parent exists if specified
    if group_data.parent_id:
        parent = group_service.get_group(group_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent group not found"
            )

    group = group_service.create_group(group_data)
    response = GroupResponse.model_validate(group)
    response.router_count = 0
    return response


@router.get("/{group_id}", response_model=GroupWithRoutersResponse)
async def get_group(
    group_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get group by ID"""
    group_service = GroupService(db)
    group = group_service.get_group(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    response = GroupWithRoutersResponse.model_validate(group)
    response.router_count = len(group.routers)
    response.router_ids = [r.id for r in group.routers]
    return response


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group_data: GroupUpdate,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a group"""
    group_service = GroupService(db)

    # Check name uniqueness if changing
    if group_data.name:
        existing = group_service.get_group_by_name(group_data.name)
        if existing and existing.id != group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group with this name already exists"
            )

    try:
        group = group_service.update_group(group_id, group_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    response = GroupResponse.model_validate(group)
    response.router_count = group_service.get_group_router_count(group.id)
    return response


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a group"""
    group_service = GroupService(db)
    success = group_service.delete_group(group_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )


@router.post("/{group_id}/routers", response_model=GroupWithRoutersResponse)
async def add_routers_to_group(
    group_id: int,
    request: AddRoutersToGroupRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Add routers to a group"""
    group_service = GroupService(db)
    group = group_service.add_routers_to_group(group_id, request.router_ids)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    response = GroupWithRoutersResponse.model_validate(group)
    response.router_count = len(group.routers)
    response.router_ids = [r.id for r in group.routers]
    return response


@router.delete("/{group_id}/routers", response_model=GroupWithRoutersResponse)
async def remove_routers_from_group(
    group_id: int,
    request: RemoveRoutersFromGroupRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Remove routers from a group"""
    group_service = GroupService(db)
    group = group_service.remove_routers_from_group(group_id, request.router_ids)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    response = GroupWithRoutersResponse.model_validate(group)
    response.router_count = len(group.routers)
    response.router_ids = [r.id for r in group.routers]
    return response


@router.get("/{group_id}/routers")
async def get_group_routers(
    group_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_GROUPS))],
    db: Annotated[Session, Depends(get_db)],
    include_children: bool = Query(False)
):
    """Get all routers in a group"""
    group_service = GroupService(db)
    routers = group_service.get_routers_in_group(group_id, include_children)

    return {
        "group_id": group_id,
        "include_children": include_children,
        "routers": [
            {
                "id": r.id,
                "ip": r.ip,
                "identity": r.identity,
                "model": r.model,
                "is_online": r.is_online
            }
            for r in routers
        ]
    }


@router.get("/search/{query}")
async def search_groups(
    query: str,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_GROUPS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Search groups by name or description"""
    group_service = GroupService(db)
    groups = group_service.search_groups(query)

    return [
        {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "router_count": group_service.get_group_router_count(g.id)
        }
        for g in groups
    ]
