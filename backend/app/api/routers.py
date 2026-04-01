"""API routes for router management"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.router import Router
from ..schemas.router import (
    RouterCreate, RouterUpdate, RouterResponse,
    RouterImport, RouterListResponse
)
from ..services.router_service import RouterService
from ..core.deps import CurrentUser, OperatorUser
from .scan import _is_newer_version

router = APIRouter(prefix="/routers", tags=["routers"])


@router.get("", response_model=RouterListResponse)
def list_routers(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Get list of all routers"""
    routers = db.query(Router).offset(skip).limit(limit).all()
    total = db.query(Router).count()
    online = db.query(Router).filter(Router.is_online == True).count()
    offline = total - online
    needs_update = db.query(Router).filter(Router.has_updates == True).count()

    return RouterListResponse(
        routers=routers,
        total=total,
        online=online,
        offline=offline,
        needs_update=needs_update
    )


@router.post("", response_model=RouterResponse, status_code=status.HTTP_201_CREATED)
def create_router(
    router_data: RouterCreate,
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """Add a new router"""
    # Check if router with this IP already exists
    existing = db.query(Router).filter(Router.ip == router_data.ip).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Router with IP {router_data.ip} already exists"
        )

    router_obj = Router(**router_data.model_dump())
    db.add(router_obj)
    db.commit()
    db.refresh(router_obj)
    return router_obj


@router.get("/{router_id}", response_model=RouterResponse)
def get_router(
    router_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get a specific router by ID"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Router with ID {router_id} not found"
        )
    return router_obj


@router.put("/{router_id}", response_model=RouterResponse)
def update_router(
    router_id: int,
    router_data: RouterUpdate,
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """Update a router"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Router with ID {router_id} not found"
        )

    update_data = router_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(router_obj, field, value)

    router_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(router_obj)
    return router_obj


@router.delete("/{router_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_router(
    router_id: int,
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """Delete a router"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Router with ID {router_id} not found"
        )

    db.delete(router_obj)
    db.commit()


@router.post("/import", response_model=RouterListResponse)
def import_routers(
    import_data: RouterImport,
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """Import routers from list.txt format"""
    hosts = RouterService.parse_host_file(import_data.content)

    if not hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid hosts found in import data"
        )

    if import_data.replace:
        # Delete all existing routers
        db.query(Router).delete()

    imported = 0
    skipped = 0

    for host in hosts:
        existing = db.query(Router).filter(Router.ip == host.ip).first()

        if existing:
            if import_data.replace:
                # Update existing
                existing.port = host.port
                existing.username = host.username
                existing.password = host.password
                existing.updated_at = datetime.utcnow()
            else:
                skipped += 1
                continue
        else:
            router_obj = Router(
                ip=host.ip,
                port=host.port,
                username=host.username,
                password=host.password
            )
            db.add(router_obj)
            imported += 1

    db.commit()

    # Return updated list
    routers = db.query(Router).all()
    total = len(routers)
    online = sum(1 for r in routers if r.is_online)

    return RouterListResponse(
        routers=routers,
        total=total,
        online=online,
        offline=total - online,
        needs_update=sum(1 for r in routers if r.has_updates)
    )


@router.post("/{router_id}/change-channel")
def change_update_channel(
    router_id: int,
    channel: str,
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """
    Change the update channel for a router via SSH.
    Valid channels: stable, long-term, testing, development
    """
    from ..services.ssh_service import SSHService
    from ..core.enums import UpdateTree
    from ..config import settings

    # Validate channel
    valid_channels = ["stable", "long-term", "testing", "development"]
    if channel not in valid_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel. Must be one of: {', '.join(valid_channels)}"
        )

    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Router with ID {router_id} not found"
        )

    # Get credentials
    username = router_obj.username or settings.DEFAULT_USERNAME
    password = router_obj.password or settings.DEFAULT_PASSWORD

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credentials available for this router"
        )

    # Change channel via SSH
    try:
        update_tree = UpdateTree(channel)
        success, message = SSHService.change_update_tree(
            ip=router_obj.ip,
            username=username,
            password=password,
            new_tree=update_tree
        )

        if success:
            # Update database with new channel
            router_obj.update_channel = channel
            router_obj.updated_at = datetime.utcnow()

            # After changing channel, connect to router and check for updates
            try:
                from ..services.routeros_rest import RouterOSClient
                import time

                client = RouterOSClient(
                    host=router_obj.ip,
                    username=username,
                    password=password,
                    port=443,
                    timeout=30
                )

                if client.connect():
                    # Check for updates and wait for result
                    try:
                        update_info = client.check_for_updates(wait=True, timeout=20)
                        if update_info:
                            installed = update_info.get('installed-version')
                            latest = update_info.get('latest-version')

                            if installed:
                                router_obj.installed_version = installed
                            if latest:
                                router_obj.latest_version = latest
                                # Check if update available
                                router_obj.has_updates = (
                                    latest != installed if latest and installed else False
                                )
                    except Exception:
                        pass

                    # Also get firmware info
                    try:
                        rb_info = client.get_routerboard()
                        if rb_info:
                            current_fw = rb_info.get('current-firmware')
                            upgrade_fw = rb_info.get('upgrade-firmware')
                            if current_fw:
                                router_obj.firmware = current_fw
                            if upgrade_fw:
                                router_obj.upgrade_firmware = upgrade_fw
                            # Only show update if upgrade > current
                            if current_fw and upgrade_fw:
                                router_obj.has_firmware_update = _is_newer_version(upgrade_fw, current_fw)
                            else:
                                router_obj.has_firmware_update = False
                    except Exception:
                        pass

                    client.close()

            except Exception as e:
                # Non-critical - channel was changed, just couldn't refresh data
                pass

            db.commit()

            return {
                "success": True,
                "message": message,
                "router_id": router_id,
                "new_channel": channel,
                "latest_version": router_obj.latest_version,
                "has_updates": router_obj.has_updates
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change channel: {str(e)}"
        )


@router.post("/import-file")
def import_routers_from_file(
    current_user: OperatorUser,
    db: Session = Depends(get_db)
):
    """Import routers from the default list.txt file"""
    import os
    from ..config import settings

    list_file = settings.BASE_DIR / "list.txt"

    if not os.path.exists(list_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="list.txt file not found"
        )

    with open(list_file, 'r') as f:
        content = f.read()

    hosts = RouterService.parse_host_file(content)

    if not hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid hosts found in list.txt"
        )

    imported = 0
    updated = 0

    for host in hosts:
        existing = db.query(Router).filter(Router.ip == host.ip).first()

        if existing:
            # Update credentials if provided
            if host.username:
                existing.username = host.username
            if host.password:
                existing.password = host.password
            existing.port = host.port
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            router_obj = Router(
                ip=host.ip,
                port=host.port,
                username=host.username,
                password=host.password
            )
            db.add(router_obj)
            imported += 1

    db.commit()

    return {
        "message": f"Import complete: {imported} new, {updated} updated",
        "imported": imported,
        "updated": updated,
        "total": imported + updated
    }
