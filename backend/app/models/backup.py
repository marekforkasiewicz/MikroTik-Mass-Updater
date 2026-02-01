"""Backup and Rollback models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship
from ..database import Base


class RouterBackup(Base):
    """Router Backup database model"""
    __tablename__ = "router_backups"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)

    # Backup info
    name = Column(String(255), nullable=False)
    backup_type = Column(String(20), nullable=False)  # config, full, export, cloud

    # File info
    file_path = Column(String(500), nullable=True)  # Local path for file-based backups
    file_size = Column(BigInteger, nullable=True)  # Size in bytes
    checksum = Column(String(64), nullable=True)  # SHA256 hash

    # Cloud backup info
    cloud_name = Column(String(255), nullable=True)  # Cloud backup name on MikroTik cloud
    secret_download_key = Column(String(255), nullable=True)  # Key for downloading from cloud

    # Router state at backup time
    router_version = Column(String(50), nullable=True)
    router_model = Column(String(255), nullable=True)
    router_identity = Column(String(255), nullable=True)

    # Backup content metadata
    includes_passwords = Column(Boolean, default=False)
    encryption_type = Column(String(20), nullable=True)  # none, aes256

    # Status
    status = Column(String(20), default="completed")  # pending, in_progress, completed, failed
    error_message = Column(Text, nullable=True)

    # Retention
    is_auto = Column(Boolean, default=False)  # Auto-created by scheduled backup
    keep_forever = Column(Boolean, default=False)  # Exempt from auto-cleanup
    expires_at = Column(DateTime, nullable=True)  # Auto-delete after this time

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    router = relationship("Router", back_populates="backups")
    creator = relationship("User")
    rollback_logs = relationship("RollbackLog", back_populates="backup", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RouterBackup(id={self.id}, router_id={self.router_id}, type={self.backup_type})>"


class RollbackLog(Base):
    """Rollback operation log"""
    __tablename__ = "rollback_logs"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    backup_id = Column(Integer, ForeignKey("router_backups.id", ondelete="SET NULL"), nullable=True)

    # Rollback details
    rollback_type = Column(String(20), nullable=False)  # restore, downgrade, config_restore
    reason = Column(Text, nullable=True)

    # State before rollback
    previous_version = Column(String(50), nullable=True)
    previous_config_hash = Column(String(64), nullable=True)

    # State after rollback
    target_version = Column(String(50), nullable=True)

    # Status
    status = Column(String(20), nullable=False)  # pending, in_progress, completed, failed
    error_message = Column(Text, nullable=True)

    # Execution details
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    initiated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Result
    result = Column(JSON, default=dict)
    reboot_required = Column(Boolean, default=False)
    reboot_completed = Column(Boolean, default=False)

    # Relationships
    router = relationship("Router")
    backup = relationship("RouterBackup", back_populates="rollback_logs")
    initiator = relationship("User")

    def __repr__(self):
        return f"<RollbackLog(id={self.id}, router_id={self.router_id}, status={self.status})>"
