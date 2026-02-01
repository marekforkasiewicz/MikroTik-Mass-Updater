"""Notification models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class NotificationChannel(Base):
    """Notification Channel configuration"""
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    # Channel type: email, slack, telegram, webhook, discord
    channel_type = Column(String(20), nullable=False)

    # Channel-specific configuration (encrypted sensitive data recommended)
    config = Column(JSON, default=dict)
    # email: {"smtp_host", "smtp_port", "username", "password", "from_address", "to_addresses"}
    # slack: {"webhook_url", "channel", "username"}
    # telegram: {"bot_token", "chat_ids"}
    # webhook: {"url", "method", "headers"}
    # discord: {"webhook_url"}

    # Status
    enabled = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    last_test = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    rules = relationship("NotificationRule", back_populates="channel", cascade="all, delete-orphan")
    logs = relationship("NotificationLog", back_populates="channel", cascade="all, delete-orphan")
    creator = relationship("User")

    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, name={self.name}, type={self.channel_type})>"


class NotificationRule(Base):
    """Notification rules - when to send notifications"""
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False)

    # Event triggers
    event_types = Column(JSON, default=list)
    # Options: router_offline, router_online, update_available, update_completed,
    # update_failed, backup_completed, backup_failed, scan_completed,
    # script_executed, health_warning, health_critical, schedule_failed

    # Filters
    router_filter = Column(JSON, default=dict)  # {"groups": [], "tags": [], "ids": []}
    severity_filter = Column(JSON, default=list)  # ["info", "warning", "critical"]

    # Throttling
    cooldown_seconds = Column(Integer, default=300)  # Min time between notifications
    max_per_hour = Column(Integer, default=10)
    aggregate = Column(Boolean, default=False)  # Aggregate multiple events into one
    aggregate_window = Column(Integer, default=60)  # seconds

    # Message customization
    custom_template = Column(Text, nullable=True)  # Jinja2 template
    include_details = Column(Boolean, default=True)

    # Status
    enabled = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    channel = relationship("NotificationChannel", back_populates="rules")

    def __repr__(self):
        return f"<NotificationRule(id={self.id}, name={self.name})>"


class NotificationLog(Base):
    """Notification delivery log"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Integer, ForeignKey("notification_rules.id", ondelete="SET NULL"), nullable=True)

    # Event details
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, default=dict)

    # Delivery status
    status = Column(String(20), nullable=False)  # pending, sent, failed, skipped
    error_message = Column(Text, nullable=True)

    # Message content
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    # Relationships
    channel = relationship("NotificationChannel", back_populates="logs")

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, event={self.event_type}, status={self.status})>"
