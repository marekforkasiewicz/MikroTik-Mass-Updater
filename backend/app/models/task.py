"""Task model for database"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from ..database import Base


class Task(Base):
    """Task database model for tracking operations"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False)  # scan, update, backup, etc.
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled

    # Configuration
    config = Column(JSON, nullable=True)  # Task configuration

    # Progress tracking
    progress = Column(Integer, default=0)
    total = Column(Integer, default=0)
    current_item = Column(String(255), nullable=True)  # Current router being processed
    current_message = Column(String(500), nullable=True)  # Current operation message

    # Results
    results = Column(JSON, nullable=True)  # Aggregated results
    error = Column(Text, nullable=True)  # Error message if failed

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.type}, status={self.status})>"

    @property
    def progress_percent(self) -> int:
        """Calculate progress percentage"""
        if self.total == 0:
            return 0
        return int((self.progress / self.total) * 100)
