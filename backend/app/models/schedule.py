"""Scheduled Task models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class ScheduledTask(Base):
    """Scheduled Task database model"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Task configuration
    task_type = Column(String(50), nullable=False)  # scan, update, backup, script, etc.
    config = Column(JSON, default=dict)  # Task-specific configuration

    # Target selection
    target_type = Column(String(20), default="all")  # all, group, specific
    target_ids = Column(JSON, default=list)  # List of router or group IDs

    # Schedule configuration (cron-style)
    cron_expression = Column(String(100), nullable=True)  # e.g., "0 2 * * *"
    timezone = Column(String(50), default="UTC")

    # Or interval-based
    interval_seconds = Column(Integer, nullable=True)  # Alternative to cron

    # Execution settings
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=5)  # 1-10, higher = more important
    max_retries = Column(Integer, default=3)
    retry_delay = Column(Integer, default=60)  # seconds
    timeout = Column(Integer, default=3600)  # seconds

    # Run conditions
    run_on_startup = Column(Boolean, default=False)
    run_if_missed = Column(Boolean, default=True)  # Run if scheduled time was missed

    # Status
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)  # success, failed, running
    last_error = Column(Text, nullable=True)
    run_count = Column(Integer, default=0)

    # Owner
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("ScheduleExecution", back_populates="schedule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, name={self.name}, type={self.task_type})>"


class ScheduleExecution(Base):
    """Schedule Execution history"""
    __tablename__ = "schedule_executions"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False)

    # Execution details
    status = Column(String(20), nullable=False)  # running, success, failed, cancelled
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results
    result = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    # Metrics
    routers_affected = Column(Integer, default=0)
    routers_success = Column(Integer, default=0)
    routers_failed = Column(Integer, default=0)

    # Trigger info
    trigger_type = Column(String(20), default="scheduled")  # scheduled, manual, startup
    triggered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    schedule = relationship("ScheduledTask", back_populates="executions")
    triggerer = relationship("User", foreign_keys=[triggered_by])

    def __repr__(self):
        return f"<ScheduleExecution(id={self.id}, schedule_id={self.schedule_id}, status={self.status})>"
