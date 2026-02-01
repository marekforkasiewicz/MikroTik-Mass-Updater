"""Compliance models for configuration compliance checking"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class ComplianceBaseline(Base):
    """Compliance baseline definition with rules"""
    __tablename__ = "compliance_baselines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    rules = Column(JSON, default=list)  # List of rule definitions
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    checks = relationship("ComplianceCheck", back_populates="baseline", cascade="all, delete-orphan")


class ComplianceCheck(Base):
    """Compliance check result"""
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    baseline_id = Column(Integer, ForeignKey("compliance_baselines.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)  # compliant, partial, non_compliant, error
    compliant_rules = Column(Integer, default=0)
    non_compliant_rules = Column(Integer, default=0)
    results = Column(JSON, default=list)  # Detailed rule results
    config_snapshot = Column(Text, nullable=True)  # Config at time of check
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    router = relationship("Router", backref="compliance_checks")
    baseline = relationship("ComplianceBaseline", back_populates="checks")


class ComplianceRule(Base):
    """Reusable compliance rule (optional - rules can also be inline in baseline)"""
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # contains, not_contains, regex_match, setting
    pattern = Column(Text, nullable=True)
    path = Column(String(200), nullable=True)  # For setting type
    setting = Column(String(100), nullable=True)  # For setting type
    expected = Column(String(500), nullable=True)  # For setting type
    severity = Column(String(20), default="warning")  # info, warning, critical
    category = Column(String(50), default="general")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
