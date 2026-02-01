"""API routes for network scanning"""

import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.router import Router
from ..models.task import Task
from ..schemas.router import QuickScanResult, FullScanResult
from ..schemas.task import TaskResponse
from ..services.scan_service import ScanService
from ..services.router_service import RouterService, HostInfo
from ..core.enums import TaskStatus, TaskType
from ..config import settings

router = APIRouter(prefix="/scan", tags=["scan"])


def run_quick_scan_task(task_id: str, router_ids: Optional[List[int]], db_url: str):
    """Background task for quick scan"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        db.commit()

        # Get routers to scan
        if router_ids:
            routers = db.query(Router).filter(Router.id.in_(router_ids)).all()
        else:
            routers = db.query(Router).all()

        task.total = len(routers)
        db.commit()

        results = []
        for i, router in enumerate(routers):
            host = HostInfo(
                ip=router.ip,
                port=router.port,
                username=router.username,
                password=router.password
            )

            result = ScanService.quick_scan_host(
                host,
                settings.DEFAULT_USERNAME,
                settings.DEFAULT_PASSWORD
            )

            # Update router status in database
            router.is_online = result.ping_ok and result.port_api_open
            router.last_scan = datetime.utcnow()
            if result.ping_ok:
                router.last_seen = datetime.utcnow()
            if result.ros_version:
                router.ros_version = result.ros_version
            if result.identity:
                router.identity = result.identity

            results.append({
                "ip": result.ip,
                "ping_ok": result.ping_ok,
                "ping_ms": result.ping_ms,
                "port_api_open": result.port_api_open,
                "port_ssh_open": result.port_ssh_open,
                "ros_version": result.ros_version,
                "identity": result.identity,
                "status": result.status
            })

            task.progress = i + 1
            task.current_item = router.ip
            db.commit()

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.utcnow()
        task.results = {
            "total": len(results),
            "online": sum(1 for r in results if r["ping_ok"]),
            "api_ok": sum(1 for r in results if r["port_api_open"]),
            "results": results
        }
        db.commit()

    except Exception as e:
        task.status = TaskStatus.FAILED.value
        task.error = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def run_full_scan_task(task_id: str, router_ids: Optional[List[int]], db_url: str):
    """Background task for full scan"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        db.commit()

        # Get routers to scan
        if router_ids:
            routers = db.query(Router).filter(Router.id.in_(router_ids)).all()
        else:
            routers = db.query(Router).all()

        task.total = len(routers)
        db.commit()

        results = []
        for i, router in enumerate(routers):
            host = HostInfo(
                ip=router.ip,
                port=router.port,
                username=router.username,
                password=router.password
            )

            result = ScanService.full_scan_host(
                host,
                settings.DEFAULT_USERNAME or "",
                settings.DEFAULT_PASSWORD or "",
                timeout=30
            )

            # Update router info in database
            if result.success:
                router.is_online = True
                router.identity = result.identity
                router.model = result.model
                router.ros_version = result.ros_version
                router.firmware = result.firmware
                router.upgrade_firmware = result.upgrade_firmware
                router.update_channel = result.update_channel
                router.installed_version = result.installed_version
                router.latest_version = result.latest_version
                router.uptime = result.uptime
                router.last_seen = datetime.utcnow()

                # Check for updates
                if result.latest_version and result.installed_version:
                    router.has_updates = result.latest_version != result.installed_version
                if result.upgrade_firmware and result.firmware:
                    router.has_firmware_update = result.upgrade_firmware != result.firmware
            else:
                router.is_online = False

            router.last_scan = datetime.utcnow()

            results.append({
                "ip": result.ip,
                "identity": result.identity,
                "model": result.model,
                "ros_version": result.ros_version,
                "firmware": result.firmware,
                "update_channel": result.update_channel,
                "installed_version": result.installed_version,
                "latest_version": result.latest_version,
                "success": result.success,
                "error": result.error
            })

            task.progress = i + 1
            task.current_item = router.ip
            db.commit()

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.utcnow()
        task.results = {
            "total": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }
        db.commit()

    except Exception as e:
        task.status = TaskStatus.FAILED.value
        task.error = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.post("/quick", response_model=TaskResponse)
def start_quick_scan(
    router_ids: Optional[List[int]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Start a quick network scan.

    Quick scan checks:
    - Ping reachability
    - API port status
    - SSH port status
    - Basic RouterOS info (if credentials available)
    """
    task = Task(
        type=TaskType.QUICK_SCAN.value,
        status=TaskStatus.PENDING.value,
        config={"router_ids": router_ids} if router_ids else None
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        run_quick_scan_task,
        task.id,
        router_ids,
        settings.DATABASE_URL
    )

    return task


@router.post("/full", response_model=TaskResponse)
def start_full_scan(
    router_ids: Optional[List[int]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Start a full network scan.

    Full scan gathers complete router information via API:
    - Identity, model, firmware
    - RouterOS version
    - Update channel and available updates
    - Uptime
    """
    task = Task(
        type=TaskType.SCAN.value,
        status=TaskStatus.PENDING.value,
        config={"router_ids": router_ids} if router_ids else None
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        run_full_scan_task,
        task.id,
        router_ids,
        settings.DATABASE_URL
    )

    return task


@router.get("/quick/single/{router_id}", response_model=QuickScanResult)
def quick_scan_single(router_id: int, db: Session = Depends(get_db)):
    """Quick scan a single router (synchronous)"""
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")

    host = HostInfo(
        ip=router.ip,
        port=router.port,
        username=router.username,
        password=router.password
    )

    result = ScanService.quick_scan_host(
        host,
        settings.DEFAULT_USERNAME,
        settings.DEFAULT_PASSWORD
    )

    # Update router status
    router.is_online = result.ping_ok and result.port_api_open
    router.last_scan = datetime.utcnow()
    if result.ping_ok:
        router.last_seen = datetime.utcnow()
    if result.ros_version:
        router.ros_version = result.ros_version
    if result.identity:
        router.identity = result.identity
    db.commit()

    return QuickScanResult(
        ip=result.ip,
        ping_ok=result.ping_ok,
        ping_ms=result.ping_ms,
        port_api_open=result.port_api_open,
        port_ssh_open=result.port_ssh_open,
        ros_version=result.ros_version,
        identity=result.identity,
        status=result.status,
        has_credentials=result.has_credentials
    )
