"""Monitoring models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from ..database import Base


class MonitoringConfig(Base):
    """Monitoring configuration per router or global"""
    __tablename__ = "monitoring_configs"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=True)

    # If router_id is null, this is the global default config
    is_global = Column(Boolean, default=False)

    # Check intervals (in seconds)
    ping_interval = Column(Integer, default=60)
    port_check_interval = Column(Integer, default=300)
    full_health_interval = Column(Integer, default=900)  # 15 minutes

    # Thresholds
    ping_timeout = Column(Float, default=2.0)  # seconds
    ping_warning_latency = Column(Float, default=100.0)  # ms
    ping_critical_latency = Column(Float, default=500.0)  # ms

    # Resource thresholds
    cpu_warning_percent = Column(Float, default=80.0)
    cpu_critical_percent = Column(Float, default=95.0)
    memory_warning_percent = Column(Float, default=80.0)
    memory_critical_percent = Column(Float, default=95.0)
    disk_warning_percent = Column(Float, default=80.0)
    disk_critical_percent = Column(Float, default=95.0)

    # What to check
    check_ping = Column(Boolean, default=True)
    check_api_port = Column(Boolean, default=True)
    check_ssh_port = Column(Boolean, default=False)
    check_resources = Column(Boolean, default=True)
    check_updates = Column(Boolean, default=True)

    # Alert settings
    alert_on_offline = Column(Boolean, default=True)
    alert_on_online = Column(Boolean, default=True)
    offline_threshold = Column(Integer, default=3)  # failures before alert

    # Status
    enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    router = relationship("Router", back_populates="monitoring_config")

    def __repr__(self):
        return f"<MonitoringConfig(id={self.id}, router_id={self.router_id})>"


class HealthCheck(Base):
    """Health check results"""
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)

    # Check type and time
    check_type = Column(String(20), nullable=False)  # ping, port, full
    checked_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(20), nullable=False)  # ok, warning, critical, unknown
    is_online = Column(Boolean, nullable=True)

    # Metrics
    latency_ms = Column(Float, nullable=True)

    # Port checks
    api_port_open = Column(Boolean, nullable=True)
    ssh_port_open = Column(Boolean, nullable=True)

    # Resource metrics (for full checks)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)

    # Additional data
    details = Column(JSON, default=dict)

    # Relationships
    router = relationship("Router")

    def __repr__(self):
        return f"<HealthCheck(id={self.id}, router_id={self.router_id}, status={self.status})>"


class AlertHistory(Base):
    """Alert history"""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=True)

    # Alert type and severity
    alert_type = Column(String(50), nullable=False)
    # router_offline, router_online, high_cpu, high_memory, high_disk,
    # high_latency, update_available, update_failed, backup_failed

    severity = Column(String(20), nullable=False)  # info, warning, critical

    # Alert content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    details = Column(JSON, default=dict)

    # Status
    status = Column(String(20), default="active")  # active, acknowledged, resolved
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    router = relationship("Router")
    acknowledger = relationship("User")

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, type={self.alert_type}, severity={self.severity})>"
