"""Router model for database"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class Router(Base):
    """Router database model"""
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), unique=True, index=True, nullable=False)
    port = Column(Integer, default=8728)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    # Router information (populated after scan)
    identity = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    ros_version = Column(String(50), nullable=True)
    firmware = Column(String(50), nullable=True)
    upgrade_firmware = Column(String(50), nullable=True)
    update_channel = Column(String(50), nullable=True)
    installed_version = Column(String(50), nullable=True)
    latest_version = Column(String(50), nullable=True)
    uptime = Column(String(100), nullable=True)

    # Status
    is_online = Column(Boolean, default=False)
    has_updates = Column(Boolean, default=False)
    has_firmware_update = Column(Boolean, default=False)

    # Organization and metadata
    tags = Column(JSON, default=list)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    last_seen = Column(DateTime, nullable=True)
    last_scan = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    groups = relationship("RouterGroup", secondary="router_group_members", back_populates="routers")
    backups = relationship("RouterBackup", back_populates="router", cascade="all, delete-orphan")
    monitoring_config = relationship("MonitoringConfig", back_populates="router", uselist=False,
                                     cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Router(id={self.id}, ip={self.ip}, identity={self.identity})>"
