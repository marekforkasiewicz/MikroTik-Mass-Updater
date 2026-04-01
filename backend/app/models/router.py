"""Router model for database"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from ..database import Base
from ..core.security import encrypt_router_password, decrypt_router_password


class Router(Base):
    """Router database model"""
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), unique=True, index=True, nullable=False)
    port = Column(Integer, default=8728)
    username = Column(String(255), nullable=True)
    _password = Column("password", String(2048), nullable=True)

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
    memory_total_mb = Column(Integer, nullable=True)
    architecture = Column(String(50), nullable=True)

    # Status
    is_online = Column(Boolean, default=False)
    has_updates = Column(Boolean, default=False)
    has_firmware_update = Column(Boolean, default=False)

    # Organization and metadata
    tags = Column(JSON, default=list)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Topology/neighbors data
    neighbors = Column(JSON, nullable=True)
    rest_port = Column(Integer, default=443)

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

    @property
    def password(self):
        """Return the decrypted router password."""
        return decrypt_router_password(self._password)

    @password.setter
    def password(self, value):
        """Encrypt router passwords before storing them."""
        self._password = encrypt_router_password(value)
