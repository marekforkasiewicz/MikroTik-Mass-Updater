"""Config Template models for Zero-Touch Provisioning"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from ..database import Base


# Association table for many-to-many relationship between profiles and templates
profile_templates = Table(
    'profile_templates',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('device_profiles.id', ondelete='CASCADE'), primary_key=True),
    Column('template_id', Integer, ForeignKey('config_templates.id', ondelete='CASCADE'), primary_key=True)
)


class ConfigTemplate(Base):
    """Configuration Template for RouterOS devices"""
    __tablename__ = "config_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="general")  # network, security, wireless, system, general
    content = Column(Text, nullable=False)  # Jinja2 template content

    # Template variables definition
    # Format: [{"name": "dns_primary", "type": "string", "default": "8.8.8.8", "required": true, "description": "Primary DNS"}]
    variables = Column(JSON, default=list)

    # Tags for organization and filtering
    tags = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profiles = relationship("DeviceProfile", secondary=profile_templates, back_populates="templates")
    deployments = relationship("TemplateDeployment", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ConfigTemplate(id={self.id}, name={self.name}, category={self.category})>"


class DeviceProfile(Base):
    """Device Profile for grouping templates and auto-assignment"""
    __tablename__ = "device_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Device matching filter
    # Format: {"model": ["hAP*", "RB*"], "architecture": ["arm", "arm64"]}
    device_filter = Column(JSON, default=dict)

    # Execution order of templates
    # Format: [template_id1, template_id2, ...]
    execution_order = Column(JSON, default=list)

    # Profile-level variable defaults
    # Format: {"dns_primary": "1.1.1.1", "ntp_server": "pool.ntp.org"}
    variables = Column(JSON, default=dict)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    templates = relationship("ConfigTemplate", secondary=profile_templates, back_populates="profiles")

    def __repr__(self):
        return f"<DeviceProfile(id={self.id}, name={self.name})>"


class TemplateDeployment(Base):
    """Record of template deployment to a router"""
    __tablename__ = "template_deployments"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('config_templates.id', ondelete='CASCADE'), nullable=False)
    router_id = Column(Integer, ForeignKey('routers.id', ondelete='CASCADE'), nullable=False)

    # Deployment details
    rendered_content = Column(Text, nullable=True)  # The actual rendered template
    variables_used = Column(JSON, default=dict)  # Variables used in rendering

    # Status: pending, running, completed, failed, rolled_back
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)

    # Rollback support
    backup_id = Column(Integer, ForeignKey('router_backups.id', ondelete='SET NULL'), nullable=True)

    # Timestamps
    deployed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    template = relationship("ConfigTemplate", back_populates="deployments")
    router = relationship("Router")
    backup = relationship("RouterBackup")

    def __repr__(self):
        return f"<TemplateDeployment(id={self.id}, template_id={self.template_id}, router_id={self.router_id}, status={self.status})>"
