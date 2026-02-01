"""API routes for MNDP neighbor discovery"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from ..services.mndp_service import get_mndp_service, DiscoveredRouter
from ..core.deps import CurrentUser

router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoveredRouterResponse(BaseModel):
    """Response model for a discovered router"""
    mac_address: str
    identity: str
    version: str
    platform: str
    board: str
    uptime_seconds: int
    uptime_formatted: str
    software_id: str
    interface_name: str
    ipv4_address: str
    ipv6_address: str
    discovered_at: datetime

    class Config:
        from_attributes = True


class DiscoveryResponse(BaseModel):
    """Response model for discovery results"""
    count: int
    discovered: List[DiscoveredRouterResponse]
    scan_duration: float
    cached: bool


class DiscoveryStatsResponse(BaseModel):
    """Response model for discovery statistics"""
    discovered_count: int
    configured_count: int
    new_devices: int  # Discovered but not configured


@router.get("", response_model=DiscoveryResponse)
async def discover_devices(
    current_user: CurrentUser,
    timeout: float = Query(default=5.0, ge=1.0, le=30.0, description="Discovery timeout in seconds"),
    force: bool = Query(default=False, description="Force new discovery, ignore cache")
):
    """
    Discover MikroTik devices on the network using MNDP protocol.

    MNDP (MikroTik Neighbor Discovery Protocol) uses UDP port 5678
    to discover devices at Layer 2 (MAC level), without requiring IP configuration.
    """
    import time
    start_time = time.time()

    mndp_service = get_mndp_service()

    # Check if using cache
    cached = False
    if not force:
        cached_results = mndp_service.get_cached()
        if cached_results and mndp_service._last_discovery_time:
            cache_age = (datetime.utcnow() - mndp_service._last_discovery_time).total_seconds()
            if cache_age < mndp_service._cache_seconds:
                cached = True

    try:
        discovered = await mndp_service.discover(timeout=timeout, force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

    duration = time.time() - start_time

    return DiscoveryResponse(
        count=len(discovered),
        discovered=[DiscoveredRouterResponse(**r.to_dict()) for r in discovered],
        scan_duration=round(duration, 2),
        cached=cached
    )


@router.get("/cached", response_model=DiscoveryResponse)
async def get_cached_discovery(current_user: CurrentUser):
    """
    Get cached discovery results without triggering a new scan.
    """
    mndp_service = get_mndp_service()
    cached_results = mndp_service.get_cached()

    return DiscoveryResponse(
        count=len(cached_results),
        discovered=[DiscoveredRouterResponse(**r.to_dict()) for r in cached_results],
        scan_duration=0,
        cached=True
    )


@router.post("/clear-cache")
async def clear_discovery_cache(current_user: CurrentUser):
    """Clear the discovery cache."""
    mndp_service = get_mndp_service()
    mndp_service.clear_cache()
    return {"message": "Discovery cache cleared"}


@router.post("/add/{mac_address}")
async def add_discovered_router(
    mac_address: str,
    current_user: CurrentUser,
    username: str = Query(default="admin"),
    password: str = Query(default="")
):
    """
    Add a discovered router to the configured routers list.
    Uses the IP address discovered via MNDP.
    """
    from sqlalchemy.orm import Session
    from fastapi import Depends
    from ..database import get_db
    from ..models.router import Router

    mndp_service = get_mndp_service()
    cached = mndp_service.get_cached()

    # Find the device by MAC
    device = next((d for d in cached if d.mac_address.upper() == mac_address.upper()), None)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with MAC {mac_address} not found in discovery cache")

    if not device.ipv4_address:
        raise HTTPException(status_code=400, detail="Device has no IPv4 address")

    # This endpoint needs db session - return info for frontend to call router create
    return {
        "message": "Use POST /api/routers to add this device",
        "suggested_data": {
            "ip": device.ipv4_address,
            "username": username,
            "password": password,
            "identity": device.identity
        }
    }
