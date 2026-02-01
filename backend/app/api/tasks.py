"""API routes for task management"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.router import Router
from ..models.task import Task
from ..schemas.task import TaskCreate, TaskResponse, TaskListResponse, TaskConfig
from ..schemas.update import UpdateConfig, UpdateResult, UpdateSummary
from ..services.update_service import UpdateService
from ..services.backup_service import BackupService
from ..services.router_service import RouterService, HostInfo
from ..services.task_log_service import TaskLogService
from ..core.enums import TaskStatus, TaskType, UpdateTree
from ..config import settings

task_logger = logging.getLogger("task_operations")

router = APIRouter(prefix="/tasks", tags=["tasks"])


def run_update_task(task_id: str, config: dict, db_url: str):
    """Background task for running updates with detailed logging"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import time

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Setup file logging for this task
    log_filename = TaskLogService.get_log_filename(task_id)
    log_filepath = TaskLogService.get_log_filepath(task_id, log_filename)

    def write_log(message: str, update_task_message: bool = False):
        """Write to both file and logger, optionally update task message for WebSocket"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} - {message}\n"
        with open(log_filepath, 'a', encoding='utf-8') as f:
            f.write(log_line)
        task_logger.info(message)

        # Update task's current_message for WebSocket if requested
        if update_task_message:
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.current_message = message[:500]  # Limit to 500 chars
                    db.commit()
            except Exception:
                pass

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        db.commit()

        write_log("=" * 70)
        write_log(f"TASK STARTED: {task_id}")
        write_log(f"Type: {task.type}")
        write_log("=" * 70)

        # Get routers to update
        router_ids = config.get("router_ids", [])
        if router_ids:
            routers = db.query(Router).filter(Router.id.in_(router_ids)).all()
        else:
            routers = db.query(Router).all()

        task.total = len(routers)
        db.commit()

        # Parse config
        update_tree = UpdateTree(config.get("update_tree", "stable"))
        auto_change_tree = config.get("auto_change_tree", False)
        upgrade_firmware = config.get("upgrade_firmware", False)
        cloud_backup = config.get("cloud_backup", False)
        cloud_password = config.get("cloud_password")
        dry_run = config.get("dry_run", False)
        timeout = config.get("timeout", 30)

        write_log(f"Configuration:")
        write_log(f"  Target update tree: {update_tree.value}")
        write_log(f"  Auto-change tree: {auto_change_tree}")
        write_log(f"  Upgrade firmware: {upgrade_firmware}")
        write_log(f"  Cloud backup: {cloud_backup}")
        write_log(f"  Dry run: {dry_run}")
        write_log(f"  Total routers: {len(routers)}")
        write_log("-" * 70)

        results = []
        successful = 0
        failed = 0

        for i, router in enumerate(routers):
            task.current_item = router.ip
            task.progress = i
            db.commit()

            write_log("")
            write_log(f"Host: {router.ip}", update_task_message=True)

            host = HostInfo(
                ip=router.ip,
                port=router.port,
                username=router.username,
                password=router.password
            )

            # Perform cloud backup first if requested
            backup_result = None
            if cloud_backup and cloud_password:
                try:
                    write_log(f"  Performing cloud backup...", update_task_message=True)
                    api = RouterService.connect(
                        host,
                        settings.DEFAULT_USERNAME or "",
                        settings.DEFAULT_PASSWORD or "",
                        timeout
                    )
                    backup_result = BackupService.perform_cloud_backup(api, cloud_password)
                    api.close()
                    if backup_result.success:
                        write_log(f"  Cloud backup: SUCCESS")
                    else:
                        write_log(f"  Cloud backup: FAILED - {backup_result.error}")
                except Exception as e:
                    backup_result = type('BackupResult', (), {
                        'success': False,
                        'error': str(e)
                    })()
                    write_log(f"  Cloud backup error: {e}")

            # Run update
            result = UpdateService.process_router_update(
                host=host,
                default_username=settings.DEFAULT_USERNAME or "",
                default_password=settings.DEFAULT_PASSWORD or "",
                desired_tree=update_tree,
                auto_change_tree=auto_change_tree,
                upgrade_firmware=upgrade_firmware,
                dry_run=dry_run,
                timeout=timeout,
                cached_latest_version=router.latest_version
            )

            # Log all messages from update
            for msg in result.messages:
                write_log(f"  {msg}", update_task_message=True)

            # Update router record
            if result.success:
                successful += 1
                router.is_online = True
                router.last_seen = datetime.utcnow()
                if result.identity:
                    router.identity = result.identity
                if result.new_version:
                    router.installed_version = result.new_version
                    router.has_updates = False
                # Update additional router info collected during update
                if result.ros_version:
                    router.ros_version = result.ros_version
                if result.update_channel:
                    router.update_channel = result.update_channel
                if result.firmware:
                    router.firmware = result.firmware
                if result.upgrade_firmware:
                    router.upgrade_firmware = result.upgrade_firmware
                    router.has_firmware_update = (result.firmware != result.upgrade_firmware)
                if result.model:
                    router.model = result.model
                write_log(f"  Status: SUCCESS")
            else:
                failed += 1
                router.is_online = False
                write_log(f"  Status: FAILED - {result.error}")

            router.last_scan = datetime.utcnow()
            db.commit()

            results.append({
                "router_id": router.id,
                "ip": result.ip,
                "identity": result.identity,
                "success": result.success,
                "previous_version": result.previous_version,
                "new_version": result.new_version,
                "firmware_upgraded": result.firmware_upgraded,
                "backup_created": backup_result.success if backup_result else False,
                "tree_changed": result.tree_changed,
                "rebooted": result.rebooted,
                "error": result.error,
                "messages": result.messages
            })

            task.progress = i + 1
            db.commit()

            write_log("-" * 70)

        # Write summary
        write_log("")
        write_log("=" * 70)
        write_log("JOB SUMMARY")
        write_log("=" * 70)
        write_log(f"Total hosts processed: {len(results)}")
        write_log(f"Successful operations: {successful}")
        write_log(f"Failed operations: {failed}")

        if failed > 0:
            write_log("")
            write_log("Failed hosts:")
            for r in results:
                if not r['success']:
                    write_log(f"  - {r['ip']}: {r['error']}")

        write_log("=" * 70)
        write_log("JOB FINISHED")
        write_log("=" * 70)

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.utcnow()
        task.results = {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "log_file": log_filename,
            "results": results
        }
        db.commit()

    except Exception as e:
        write_log(f"TASK ERROR: {type(e).__name__}: {e}")
        task.status = TaskStatus.FAILED.value
        task.error = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.get("", response_model=TaskListResponse)
def list_tasks(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of tasks"""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()

    return TaskListResponse(tasks=tasks, total=total)


@router.post("", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Create a new task"""
    config_dict = task_data.config.model_dump() if task_data.config else {}

    task = Task(
        type=task_data.type.value,
        status=TaskStatus.PENDING.value,
        config=config_dict
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Start background task based on type
    if task_data.type == TaskType.UPDATE:
        background_tasks.add_task(
            run_update_task,
            task.id,
            config_dict,
            settings.DATABASE_URL
        )

    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task status"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """Cancel a running task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task.status} status"
        )

    task.status = TaskStatus.CANCELLED.value
    task.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Task cancelled", "task_id": task_id}


@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Cannot delete a running task")

    db.delete(task)
    db.commit()

    return {"message": "Task deleted", "task_id": task_id}


@router.post("/update", response_model=TaskResponse)
def start_update_task(
    config: UpdateConfig,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Start an update task with specific configuration"""
    config_dict = config.model_dump()

    task = Task(
        type=TaskType.UPDATE.value,
        status=TaskStatus.PENDING.value,
        config=config_dict
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        run_update_task,
        task.id,
        config_dict,
        settings.DATABASE_URL
    )

    return task


# ============== Log Files Management Endpoints ==============

@router.get("/logs/files")
def list_log_files():
    """List all log files with metadata and summary"""
    files = TaskLogService.list_log_files()
    stats = TaskLogService.get_statistics()
    return {
        "files": files,
        "total": len(files),
        "statistics": stats
    }


@router.get("/logs/files/{filename}")
def get_log_file(filename: str, raw: bool = False):
    """Get content of a specific log file. Use raw=true for plain text."""
    try:
        if raw:
            content = TaskLogService.read_log_file(filename)
            return PlainTextResponse(content)
        else:
            # Return parsed structured data
            parsed = TaskLogService.parse_log_file(filename)
            return parsed
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/logs/files/{filename}/raw", response_class=PlainTextResponse)
def get_log_file_raw(filename: str):
    """Get raw content of a log file"""
    try:
        content = TaskLogService.read_log_file(filename)
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


@router.delete("/logs/files/{filename}")
def delete_log_file(filename: str):
    """Delete a specific log file"""
    try:
        TaskLogService.delete_log_file(filename)
        return {"message": "Log file deleted", "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


@router.delete("/logs/cleanup")
def cleanup_old_logs(days: int = 30):
    """Delete log files older than specified days"""
    deleted = TaskLogService.delete_old_logs(days)
    return {
        "message": f"Deleted {deleted} log files older than {days} days",
        "deleted_count": deleted
    }


@router.get("/logs/statistics")
def get_log_statistics():
    """Get overall statistics from all log files"""
    return TaskLogService.get_statistics()
