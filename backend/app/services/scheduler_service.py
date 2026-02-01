"""Scheduler service for managing scheduled tasks"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from croniter import croniter

from ..models.schedule import ScheduledTask, ScheduleExecution
from ..models.router import Router
from ..models.group import RouterGroup
from ..schemas.schedule import ScheduleCreate, ScheduleUpdate
from ..core.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks"""

    def __init__(self, db: Session):
        self.db = db
        self.scheduler = get_scheduler()

    def create_schedule(self, schedule_data: ScheduleCreate, user_id: Optional[int] = None) -> ScheduledTask:
        """Create a new scheduled task"""
        schedule = ScheduledTask(
            name=schedule_data.name,
            description=schedule_data.description,
            task_type=schedule_data.task_type,
            config=schedule_data.config,
            target_type=schedule_data.target_type,
            target_ids=schedule_data.target_ids,
            cron_expression=schedule_data.cron_expression,
            timezone=schedule_data.timezone,
            interval_seconds=schedule_data.interval_seconds,
            enabled=schedule_data.enabled,
            priority=schedule_data.priority,
            max_retries=schedule_data.max_retries,
            retry_delay=schedule_data.retry_delay,
            timeout=schedule_data.timeout,
            run_on_startup=schedule_data.run_on_startup,
            run_if_missed=schedule_data.run_if_missed,
            created_by=user_id
        )

        # Calculate next run time
        if schedule.cron_expression:
            cron = croniter(schedule.cron_expression, datetime.utcnow())
            schedule.next_run = cron.get_next(datetime)
        elif schedule.interval_seconds:
            schedule.next_run = datetime.utcnow()

        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)

        # Register with APScheduler if enabled
        if schedule.enabled:
            self._register_job(schedule)

        logger.info(f"Schedule created: {schedule.name}")
        return schedule

    def update_schedule(self, schedule_id: int, schedule_data: ScheduleUpdate) -> Optional[ScheduledTask]:
        """Update a scheduled task"""
        schedule = self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            return None

        # Remove old job if exists
        if schedule.enabled:
            self._unregister_job(schedule)

        update_data = schedule_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(schedule, field, value)

        # Recalculate next run time
        if schedule.cron_expression:
            cron = croniter(schedule.cron_expression, datetime.utcnow())
            schedule.next_run = cron.get_next(datetime)
        elif schedule.interval_seconds:
            schedule.next_run = datetime.utcnow()

        self.db.commit()
        self.db.refresh(schedule)

        # Re-register if enabled
        if schedule.enabled:
            self._register_job(schedule)

        logger.info(f"Schedule updated: {schedule.name}")
        return schedule

    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a scheduled task"""
        schedule = self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            return False

        # Remove from scheduler
        self._unregister_job(schedule)

        self.db.delete(schedule)
        self.db.commit()
        logger.info(f"Schedule deleted: {schedule.name}")
        return True

    def get_schedule(self, schedule_id: int) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID"""
        return self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()

    def list_schedules(self, skip: int = 0, limit: int = 100) -> Tuple[List[ScheduledTask], int]:
        """List all scheduled tasks"""
        total = self.db.query(ScheduledTask).count()
        schedules = self.db.query(ScheduledTask).offset(skip).limit(limit).all()
        return schedules, total

    def enable_schedule(self, schedule_id: int) -> Optional[ScheduledTask]:
        """Enable a scheduled task"""
        schedule = self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            return None

        schedule.enabled = True
        self.db.commit()
        self._register_job(schedule)
        return schedule

    def disable_schedule(self, schedule_id: int) -> Optional[ScheduledTask]:
        """Disable a scheduled task"""
        schedule = self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            return None

        schedule.enabled = False
        self.db.commit()
        self._unregister_job(schedule)
        return schedule

    def run_now(self, schedule_id: int, user_id: Optional[int] = None) -> Optional[ScheduleExecution]:
        """Run a scheduled task immediately"""
        schedule = self.db.query(ScheduledTask).filter(ScheduledTask.id == schedule_id).first()
        if not schedule:
            return None

        execution = ScheduleExecution(
            schedule_id=schedule.id,
            status="running",
            trigger_type="manual",
            triggered_by=user_id
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # Execute task in background
        from .task_executor import execute_scheduled_task
        execute_scheduled_task(schedule.id, execution.id)

        return execution

    def get_executions(
        self,
        schedule_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[ScheduleExecution], int]:
        """Get execution history for a schedule"""
        total = self.db.query(ScheduleExecution).filter(
            ScheduleExecution.schedule_id == schedule_id
        ).count()

        executions = self.db.query(ScheduleExecution).filter(
            ScheduleExecution.schedule_id == schedule_id
        ).order_by(ScheduleExecution.started_at.desc()).offset(skip).limit(limit).all()

        return executions, total

    def get_target_routers(self, schedule: ScheduledTask) -> List[Router]:
        """Get list of routers targeted by this schedule"""
        if schedule.target_type == "all":
            return self.db.query(Router).all()
        elif schedule.target_type == "group":
            routers = []
            groups = self.db.query(RouterGroup).filter(
                RouterGroup.id.in_(schedule.target_ids)
            ).all()
            for group in groups:
                routers.extend(group.routers)
            return list(set(routers))  # Remove duplicates
        elif schedule.target_type == "specific":
            return self.db.query(Router).filter(
                Router.id.in_(schedule.target_ids)
            ).all()
        return []

    def _register_job(self, schedule: ScheduledTask):
        """Register a job with APScheduler"""
        job_id = f"schedule_{schedule.id}"

        try:
            if schedule.cron_expression:
                self.scheduler.add_cron_job(
                    job_id=job_id,
                    func=self._execute_schedule,
                    cron_expression=schedule.cron_expression,
                    kwargs={"schedule_id": schedule.id},
                    name=schedule.name
                )
            elif schedule.interval_seconds:
                self.scheduler.add_interval_job(
                    job_id=job_id,
                    func=self._execute_schedule,
                    seconds=schedule.interval_seconds,
                    kwargs={"schedule_id": schedule.id},
                    name=schedule.name
                )
            logger.info(f"Job registered: {job_id}")
        except Exception as e:
            logger.error(f"Failed to register job {job_id}: {e}")

    def _unregister_job(self, schedule: ScheduledTask):
        """Unregister a job from APScheduler"""
        job_id = f"schedule_{schedule.id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job unregistered: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to unregister job {job_id}: {e}")

    def _execute_schedule(self, schedule_id: int):
        """Execute a scheduled task (called by APScheduler)"""
        from .task_executor import execute_scheduled_task
        execute_scheduled_task(schedule_id)

    def get_cron_description(self, cron_expression: str) -> dict:
        """Get human-readable description of cron expression"""
        try:
            from cronstrue import ExpressionDescriptor
            description = ExpressionDescriptor(cron_expression).get_description()

            # Get next 5 run times
            cron = croniter(cron_expression, datetime.utcnow())
            next_runs = [cron.get_next(datetime) for _ in range(5)]

            return {
                "cron": cron_expression,
                "description": description,
                "next_runs": next_runs
            }
        except Exception as e:
            return {
                "cron": cron_expression,
                "description": f"Invalid cron expression: {e}",
                "next_runs": []
            }

    def sync_all_schedules(self):
        """Sync all enabled schedules with APScheduler"""
        schedules = self.db.query(ScheduledTask).filter(ScheduledTask.enabled == True).all()
        for schedule in schedules:
            self._register_job(schedule)
        logger.info(f"Synced {len(schedules)} schedules with APScheduler")
