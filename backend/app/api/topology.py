"""Topology API endpoints for network visualization"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.topology_service import TopologyService
from ..core.deps import require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/topology", tags=["Topology"])


@router.get("/map")
async def get_topology_map(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get network topology map data for visualization"""
    topology_service = TopologyService(db)
    return topology_service.get_topology_map()


@router.get("/neighbors/{router_id}")
async def get_router_neighbors(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get neighbors for a specific router"""
    topology_service = TopologyService(db)
    result = topology_service.get_router_neighbors(router_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/neighbors/{router_id}/refresh")
async def refresh_router_neighbors(
    router_id: int,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Refresh neighbor data for a specific router"""
    topology_service = TopologyService(db)
    result = await topology_service.refresh_neighbors(router_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/neighbors/refresh-all")
async def refresh_all_neighbors(
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Refresh neighbor data for all online routers"""
    topology_service = TopologyService(db)
    return await topology_service.refresh_all_neighbors()


@router.post("/layout")
async def save_layout(
    layout: dict,
    current_user: Annotated[None, Depends(require_permission(Permission.MANAGE_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Save user-defined node positions"""
    topology_service = TopologyService(db)
    success = topology_service.save_layout(layout)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save layout")

    return {"message": "Layout saved"}


@router.get("/layout")
async def get_layout(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_TOPOLOGY))],
    db: Annotated[Session, Depends(get_db)]
):
    """Get saved node positions"""
    topology_service = TopologyService(db)
    layout = topology_service.get_layout()

    return {"layout": layout}
