"""Task Log model for detailed operation logging"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class TaskLog(Base):
    """Detailed log entries for task operations"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Router information
    router_ip = Column(String(45), nullable=False)
    router_identity = Column(String(255), nullable=True)
    router_model = Column(String(255), nullable=True)

    # Version information
    ros_version = Column(String(50), nullable=True)
    current_firmware = Column(String(50), nullable=True)
    upgrade_firmware = Column(String(50), nullable=True)
    installed_version = Column(String(50), nullable=True)
    latest_version = Column(String(50), nullable=True)
    update_channel = Column(String(50), nullable=True)

    # Operation status
    success = Column(Boolean, default=False)
    error = Column(Text, nullable=True)

    # Detailed log messages
    log_messages = Column(Text, nullable=True)  # Newline-separated log entries

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<TaskLog(id={self.id}, task_id={self.task_id}, router_ip={self.router_ip}, success={self.success})>"

    def add_message(self, message: str):
        """Add a log message"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        if self.log_messages:
            self.log_messages += f"\n{entry}"
        else:
            self.log_messages = entry

    def get_messages_list(self) -> list:
        """Get log messages as a list"""
        if not self.log_messages:
            return []
        return self.log_messages.split("\n")
