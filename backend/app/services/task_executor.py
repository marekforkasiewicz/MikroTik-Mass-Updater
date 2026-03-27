"""Task executor for scheduled and background tasks"""

import logging
from datetime import datetime
from typing import Optional

from ..database import SessionLocal
from ..models.schedule import ScheduledTask, ScheduleExecution
from ..models.router import Router

logger = logging.getLogger(__name__)


def execute_scheduled_task(schedule_id: int, execution_id: Optional[int] = None):
    """Execute a scheduled task"""
    db = SessionLocal()

    try:
        schedule = db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        # Create or get execution record
        if execution_id:
            execution = db.query(ScheduleExecution).filter(
                ScheduleExecution.id == execution_id
            ).first()
        else:
            execution = ScheduleExecution(
                schedule_id=schedule.id,
                status="running",
                trigger_type="scheduled"
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

        # Update schedule
        schedule.last_run = datetime.utcnow()
        schedule.run_count += 1
        db.commit()

        try:
            # Get target routers
            routers = _get_target_routers(db, schedule)
            execution.routers_affected = len(routers)
            db.commit()

            # Execute based on task type
            if schedule.task_type == "scan":
                _execute_scan(db, routers, schedule.config, execution)
            elif schedule.task_type == "quick_scan":
                _execute_quick_scan(db, routers, schedule.config, execution)
            elif schedule.task_type == "update":
                _execute_update(db, routers, schedule.config, execution)
            elif schedule.task_type == "backup":
                _execute_backup(db, routers, schedule.config, execution)
            elif schedule.task_type == "script":
                _execute_script(db, routers, schedule.config, execution)
            elif schedule.task_type == "health_check":
                _execute_health_check(db, routers, schedule.config, execution)

            execution.status = "success"
            schedule.last_status = "success"
            schedule.last_error = None

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            schedule.last_status = "failed"
            schedule.last_error = str(e)
            logger.error(f"Scheduled task {schedule.name} failed: {e}")

        execution.completed_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )

        # Calculate next run
        if schedule.cron_expression:
            from croniter import croniter
            cron = croniter(schedule.cron_expression, datetime.utcnow())
            schedule.next_run = cron.get_next(datetime)
        elif schedule.interval_seconds:
            from datetime import timedelta
            schedule.next_run = datetime.utcnow() + timedelta(seconds=schedule.interval_seconds)

        db.commit()

    except Exception as e:
        logger.error(f"Task executor error: {e}")
        db.rollback()
    finally:
        db.close()


def _get_target_routers(db, schedule: ScheduledTask):
    """Get target routers for schedule"""
    if schedule.target_type == "all":
        return db.query(Router).all()
    elif schedule.target_type == "group":
        from ..models.group import RouterGroup
        routers = []
        groups = db.query(RouterGroup).filter(
            RouterGroup.id.in_(schedule.target_ids or [])
        ).all()
        for group in groups:
            routers.extend(group.routers)
        return list(set(routers))
    elif schedule.target_type == "specific":
        return db.query(Router).filter(
            Router.id.in_(schedule.target_ids or [])
        ).all()
    return []


def _execute_scan(db, routers, config, execution):
    """Execute full scan on routers"""
    from .scan_service import ScanService

    scan_service = ScanService(db)
    success = 0
    failed = 0

    for router in routers:
        try:
            scan_service.full_scan_router(router)
            success += 1
        except Exception as e:
            logger.warning(f"Scan failed for {router.ip}: {e}")
            failed += 1

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"scanned": success, "failed": failed}
    db.commit()


def _execute_quick_scan(db, routers, config, execution):
    """Execute quick scan on routers"""
    from .scan_service import ScanService

    scan_service = ScanService(db)
    success = 0
    failed = 0

    for router in routers:
        try:
            result = scan_service.quick_scan_router(router.ip, router.port)
            if result.get("reachable"):
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning(f"Quick scan failed for {router.ip}: {e}")
            failed += 1

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"online": success, "offline": failed}
    db.commit()


def _execute_update(db, routers, config, execution):
    """Execute update on routers"""
    from .update_service import UpdateService

    update_service = UpdateService(db)
    success = 0
    failed = 0
    results = []

    for router in routers:
        try:
            result = update_service.update_router(
                router,
                update_tree=config.get("update_tree", "stable"),
                backup_first=config.get("backup_first", True),
                dry_run=config.get("dry_run", False)
            )
            if result.get("success"):
                success += 1
            else:
                failed += 1
            results.append(result)
        except Exception as e:
            logger.warning(f"Update failed for {router.ip}: {e}")
            failed += 1
            results.append({"ip": router.ip, "error": str(e)})

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"updated": success, "failed": failed, "details": results}
    db.commit()


def _execute_backup(db, routers, config, execution):
    """Execute backup on routers"""
    from .rollback_service import RollbackService
    from ..schemas.backup import BackupCreate

    rollback_service = RollbackService(db)
    success = 0
    failed = 0

    backup_type = config.get("backup_type", "config")

    for router in routers:
        try:
            backup_data = BackupCreate(
                router_id=router.id,
                name=f"scheduled_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                backup_type=backup_type
            )
            backup = rollback_service.create_backup(backup_data)
            if backup.status == "completed":
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning(f"Backup failed for {router.ip}: {e}")
            failed += 1

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"backed_up": success, "failed": failed}
    db.commit()


def _execute_script(db, routers, config, execution):
    """Execute script on routers"""
    from .script_service import ScriptService

    script_service = ScriptService(db)
    success = 0
    failed = 0

    script_id = config.get("script_id")
    variables = config.get("variables", {})

    if not script_id:
        execution.error_message = "No script_id in config"
        return

    for router in routers:
        try:
            result = script_service.execute_script(
                script_id=script_id,
                router_id=router.id,
                variables=variables
            )
            if result.status == "success":
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning(f"Script execution failed for {router.ip}: {e}")
            failed += 1

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"executed": success, "failed": failed}
    db.commit()


def _execute_health_check(db, routers, config, execution):
    """Execute health check on routers"""
    import asyncio
    from .monitoring_service import MonitoringService

    monitoring_service = MonitoringService(db)
    success = 0
    failed = 0

    check_type = config.get("check_type", "ping")

    async def run_checks():
        nonlocal success, failed
        for router in routers:
            try:
                check = await monitoring_service.check_router(router, check_type)
                if check.status in ["ok", "warning"]:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Health check failed for {router.ip}: {e}")
                failed += 1

    # Run async function
    try:
        asyncio.get_running_loop()
        # Already in async context - run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, run_checks()).result()
    except RuntimeError:
        # No running loop - safe to use asyncio.run
        asyncio.run(run_checks())

    execution.routers_success = success
    execution.routers_failed = failed
    execution.result = {"checked": success, "failed": failed}
    db.commit()
