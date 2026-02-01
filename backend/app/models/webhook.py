"""Webhook models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class Webhook(Base):
    """Webhook configuration"""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Endpoint configuration
    url = Column(String(500), nullable=False)
    method = Column(String(10), default="POST")  # POST, PUT

    # Headers and authentication
    headers = Column(JSON, default=dict)  # Custom headers
    auth_type = Column(String(20), nullable=True)  # none, basic, bearer, custom
    auth_config = Column(JSON, default=dict)  # Auth-specific config

    # Payload configuration
    content_type = Column(String(50), default="application/json")
    payload_template = Column(Text, nullable=True)  # Jinja2 template
    include_signature = Column(Boolean, default=True)  # HMAC signature
    secret_key = Column(String(255), nullable=True)  # For signature

    # Events to trigger on
    events = Column(JSON, default=list)
    # router_added, router_removed, router_updated, router_offline, router_online,
    # scan_completed, update_started, update_completed, update_failed,
    # backup_created, backup_failed, script_executed, alert_created

    # Filters
    router_filter = Column(JSON, default=dict)  # {"groups": [], "tags": [], "ids": []}

    # Retry settings
    retry_count = Column(Integer, default=3)
    retry_delay = Column(Integer, default=60)  # seconds
    timeout = Column(Integer, default=30)  # seconds

    # Status
    enabled = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    last_triggered = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)  # success, failed

    # Stats
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)

    # Ownership
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url[:50]})>"


class WebhookDelivery(Base):
    """Webhook delivery log"""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)

    # Event that triggered this delivery
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, default=dict)

    # Request details
    request_url = Column(String(500), nullable=False)
    request_method = Column(String(10), nullable=False)
    request_headers = Column(JSON, default=dict)
    request_body = Column(Text, nullable=True)

    # Response details
    response_status = Column(Integer, nullable=True)
    response_headers = Column(JSON, default=dict)
    response_body = Column(Text, nullable=True)

    # Delivery status
    status = Column(String(20), nullable=False)  # pending, success, failed, retrying
    attempt_count = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self):
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status={self.status})>"
