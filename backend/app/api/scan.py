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
import re

router = APIRouter(prefix="/scan", tags=["scan"])


def _parse_version(version_str: str) -> tuple:
    """
    Parse MikroTik version string into comparable tuple.
    Examples: 7.21.2, 7.22beta6, 7.21rc6
    Returns tuple: (major, minor, patch, prerelease_type, prerelease_num)
    prerelease_type: 0=stable, -1=rc, -2=beta, -3=alpha
    """
    if not version_str:
        return (0, 0, 0, 0, 0)

    # Remove any extra text after version (like "(testing) 2026-01-09...")
    version_str = version_str.split()[0] if ' ' in version_str else version_str

    # Match version pattern: 7.21.2 or 7.22beta6 or 7.21rc6
    match = re.match(r'^(\d+)\.(\d+)(?:\.(\d+))?(?:(alpha|beta|rc)(\d+))?', version_str, re.IGNORECASE)
    if not match:
        return (0, 0, 0, 0, 0)

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3) or 0)

    prerelease_type = 0  # stable
    prerelease_num = 0

    if match.group(4):
        pr_type = match.group(4).lower()
        prerelease_num = int(match.group(5))
        if pr_type == 'alpha':
            prerelease_type = -3
        elif pr_type == 'beta':
            prerelease_type = -2
        elif pr_type == 'rc':
            prerelease_type = -1

    return (major, minor, patch, prerelease_type, prerelease_num)


def _is_newer_version(latest: str, installed: str) -> bool:
    """
    Check if latest version is newer than installed version.
    Returns True if update is available.
    """
    if not latest or not installed:
        return False

    latest_parsed = _parse_version(latest)
    installed_parsed = _parse_version(installed)

    return latest_parsed > installed_parsed


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

                # Check for updates - compare versions properly
                # Use result.latest_version if available, otherwise use cached versions
                latest_version = result.latest_version
                if not latest_version and result.update_channel:
                    # Get latest version for this channel from our cache
                    from .versions import get_cached_versions
                    try:
                        versions = get_cached_versions()
                        channel_info = versions.get(result.update_channel)
                        if channel_info:
                            latest_version = channel_info.get('version')
                            router.latest_version = latest_version
                    except Exception:
                        pass

                if latest_version and result.installed_version:
                    router.has_updates = _is_newer_version(
                        latest_version,
                        result.installed_version
                    )
                if result.upgrade_firmware and result.firmware:
                    router.has_firmware_update = _is_newer_version(
                        result.upgrade_firmware,
                        result.firmware
                    )
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
        # Also update installed_version to match ros_version (extract version without build info)
        # e.g., "7.22beta6 (development)" -> "7.22beta6"
        version_part = result.ros_version.split()[0] if result.ros_version else None
        if version_part:
            router.installed_version = version_part
            # If installed matches latest, no more updates needed
            if router.latest_version and version_part == router.latest_version:
                router.has_updates = False
    if result.identity:
        router.identity = result.identity

    # If router is online with API, also fetch firmware info
    if result.port_api_open and result.has_credentials:
        try:
            from ..services.routeros_rest import RouterOSClient
            username = host.username or settings.DEFAULT_USERNAME
            password = host.password or settings.DEFAULT_PASSWORD
            client = RouterOSClient(
                host=host.ip,
                username=username,
                password=password,
                port=443,
                timeout=10
            )
            try:
                if client.connect():
                    rb_info = client.get_routerboard()
                    if rb_info:
                        router.firmware = rb_info.get('current-firmware')
                        router.upgrade_firmware = rb_info.get('upgrade-firmware')
                        # Only show firmware update if upgrade > current (not downgrade)
                        if router.firmware and router.upgrade_firmware:
                            router.has_firmware_update = _is_newer_version(
                                router.upgrade_firmware, router.firmware
                            )
                        else:
                            router.has_firmware_update = False
            finally:
                client.close()
        except Exception:
            pass  # Non-critical, continue without firmware update

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


@router.get("/firmware/{router_id}")
def check_firmware_status(router_id: int, db: Session = Depends(get_db)):
    """Check firmware status of a single router"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router not found")

    host = HostInfo(
        ip=router_obj.ip,
        port=router_obj.port,
        username=router_obj.username,
        password=router_obj.password
    )

    try:
        from ..services.routeros_rest import RouterOSClient
        client = RouterOSClient(
            host=router_obj.ip,
            username=host.username or settings.DEFAULT_USERNAME,
            password=host.password or settings.DEFAULT_PASSWORD,
            port=443,
            timeout=15
        )

        if not client.connect():
            raise Exception("Failed to connect to router REST API")

        # Get firmware info
        firmware_info = {}
        try:
            rb = client.get_routerboard()
            if rb:
                firmware_info = {
                    'current_firmware': rb.get('current-firmware'),
                    'upgrade_firmware': rb.get('upgrade-firmware'),
                    'model': rb.get('model'),
                    'serial_number': rb.get('serial-number'),
                    'needs_upgrade': _is_newer_version(
                        rb.get('upgrade-firmware'), rb.get('current-firmware')
                    ) if rb.get('upgrade-firmware') and rb.get('current-firmware') else False
                }
        except Exception as e:
            firmware_info = {'error': str(e)}

        # Get RouterOS version
        ros_version = None
        try:
            resource = client.get_resources()
            if resource:
                ros_version = resource.get('version')
        except Exception:
            pass

        client.close()

        # Update router record
        if firmware_info.get('current_firmware'):
            router_obj.firmware = firmware_info['current_firmware']
        if firmware_info.get('upgrade_firmware'):
            router_obj.upgrade_firmware = firmware_info['upgrade_firmware']
        router_obj.has_firmware_update = firmware_info.get('needs_upgrade', False)
        router_obj.is_online = True
        router_obj.last_seen = datetime.utcnow()
        if ros_version:
            router_obj.ros_version = ros_version
        db.commit()

        return {
            'ip': router_obj.ip,
            'identity': router_obj.identity,
            'ros_version': ros_version,
            **firmware_info,
            'success': True
        }

    except Exception as e:
        return {
            'ip': router_obj.ip,
            'identity': router_obj.identity,
            'error': str(e),
            'success': False
        }
