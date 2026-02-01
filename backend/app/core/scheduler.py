"""APScheduler configuration and management"""

import logging
from datetime import datetime
from typing import Optional, Callable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Singleton manager for APScheduler"""

    _instance: Optional["SchedulerManager"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Get or create scheduler instance"""
        if self._scheduler is None:
            self._init_scheduler()
        return self._scheduler

    def _init_scheduler(self):
        """Initialize the scheduler with SQLAlchemy job store"""
        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
        }

        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }

        job_defaults = {
            'coalesce': True,  # Combine missed runs into single run
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 3600  # Allow up to 1 hour late execution
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        logger.info("Scheduler initialized")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shut down")

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        replace_existing: bool = True
    ) -> Any:
        """Add a cron-based job"""
        # Parse cron expression (minute hour day month day_of_week)
        parts = cron_expression.split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )
        elif len(parts) == 6:
            trigger = CronTrigger(
                second=parts[0],
                minute=parts[1],
                hour=parts[2],
                day=parts[3],
                month=parts[4],
                day_of_week=parts[5]
            )
        else:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        return self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name or job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=replace_existing
        )

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: int,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        replace_existing: bool = True,
        start_date: Optional[datetime] = None
    ) -> Any:
        """Add an interval-based job"""
        trigger = IntervalTrigger(seconds=seconds, start_date=start_date)

        return self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name or job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=replace_existing
        )

    def remove_job(self, job_id: str):
        """Remove a job by ID"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job {job_id} removed")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")

    def pause_job(self, job_id: str):
        """Pause a job"""
        self.scheduler.pause_job(job_id)
        logger.info(f"Job {job_id} paused")

    def resume_job(self, job_id: str):
        """Resume a paused job"""
        self.scheduler.resume_job(job_id)
        logger.info(f"Job {job_id} resumed")

    def get_job(self, job_id: str):
        """Get job by ID"""
        return self.scheduler.get_job(job_id)

    def get_jobs(self):
        """Get all jobs"""
        return self.scheduler.get_jobs()

    def run_job_now(self, job_id: str):
        """Run a job immediately"""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Job {job_id} scheduled for immediate execution")
        else:
            raise ValueError(f"Job {job_id} not found")


# Global scheduler manager instance
scheduler_manager = SchedulerManager()


def get_scheduler() -> SchedulerManager:
    """Get the scheduler manager instance"""
    return scheduler_manager
