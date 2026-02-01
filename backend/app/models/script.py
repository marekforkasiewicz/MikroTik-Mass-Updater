"""Custom Script models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class CustomScript(Base):
    """Custom Script database model"""
    __tablename__ = "custom_scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Script content
    script_type = Column(String(20), default="routeros")  # routeros, ssh
    content = Column(Text, nullable=False)

    # Variables that can be passed at runtime
    variables = Column(JSON, default=list)
    # [{"name": "var1", "type": "string", "default": "", "required": true}]

    # Execution settings
    timeout = Column(Integer, default=60)  # seconds
    requires_reboot = Column(Boolean, default=False)
    dangerous = Column(Boolean, default=False)  # Requires extra confirmation

    # Categorization
    category = Column(String(50), default="general")  # general, security, network, system
    tags = Column(JSON, default=list)

    # Permissions
    allowed_roles = Column(JSON, default=["admin", "operator"])

    # Status
    enabled = Column(Boolean, default=True)
    validated = Column(Boolean, default=False)  # Has been syntax-checked

    # Usage stats
    execution_count = Column(Integer, default=0)
    last_executed = Column(DateTime, nullable=True)

    # Ownership
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    executions = relationship("ScriptExecution", back_populates="script", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomScript(id={self.id}, name={self.name})>"


class ScriptExecution(Base):
    """Script Execution log"""
    __tablename__ = "script_executions"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("custom_scripts.id", ondelete="CASCADE"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)

    # Execution details
    variables_used = Column(JSON, default=dict)  # Variables passed at runtime

    # Status
    status = Column(String(20), nullable=False)  # pending, running, success, failed

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Results
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    return_value = Column(JSON, nullable=True)

    # User
    executed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    script = relationship("CustomScript", back_populates="executions")
    router = relationship("Router")
    executor = relationship("User")

    def __repr__(self):
        return f"<ScriptExecution(id={self.id}, script_id={self.script_id}, status={self.status})>"
