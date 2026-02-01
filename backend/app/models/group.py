"""Router Group models"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from ..database import Base


# Association table for many-to-many relationship between groups and routers
router_group_members = Table(
    'router_group_members',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('router_groups.id', ondelete='CASCADE'), primary_key=True),
    Column('router_id', Integer, ForeignKey('routers.id', ondelete='CASCADE'), primary_key=True)
)


class RouterGroup(Base):
    """Router Group database model"""
    __tablename__ = "router_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#3498db")  # Hex color for UI
    icon = Column(String(50), default="folder")  # Icon name for UI

    # Parent group for hierarchical structure
    parent_id = Column(Integer, ForeignKey('router_groups.id', ondelete='SET NULL'), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("RouterGroup", remote_side=[id], backref="children")
    routers = relationship("Router", secondary=router_group_members, back_populates="groups")

    def __repr__(self):
        return f"<RouterGroup(id={self.id}, name={self.name})>"
