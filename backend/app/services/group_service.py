"""Group service for managing router groups"""

import logging
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from ..models.group import RouterGroup
from ..models.router import Router
from ..schemas.group import GroupCreate, GroupUpdate

logger = logging.getLogger(__name__)


class GroupService:
    """Service for managing router groups"""

    def __init__(self, db: Session):
        self.db = db

    def create_group(self, group_data: GroupCreate) -> RouterGroup:
        """Create a new router group"""
        group = RouterGroup(
            name=group_data.name,
            description=group_data.description,
            color=group_data.color,
            icon=group_data.icon,
            parent_id=group_data.parent_id
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Group created: {group.name}")
        return group

    def update_group(self, group_id: int, group_data: GroupUpdate) -> Optional[RouterGroup]:
        """Update a router group"""
        group = self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
        if not group:
            return None

        update_data = group_data.model_dump(exclude_unset=True)

        # Prevent circular parent reference
        if "parent_id" in update_data and update_data["parent_id"]:
            if update_data["parent_id"] == group_id:
                raise ValueError("Group cannot be its own parent")
            # Check for circular reference in hierarchy
            if self._would_create_cycle(group_id, update_data["parent_id"]):
                raise ValueError("This would create a circular reference")

        for field, value in update_data.items():
            setattr(group, field, value)

        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Group updated: {group.name}")
        return group

    def delete_group(self, group_id: int) -> bool:
        """Delete a router group"""
        group = self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
        if not group:
            return False

        # Move children to parent (or make them root-level)
        for child in group.children:
            child.parent_id = group.parent_id

        self.db.delete(group)
        self.db.commit()
        logger.info(f"Group deleted: {group.name}")
        return True

    def get_group(self, group_id: int) -> Optional[RouterGroup]:
        """Get a group by ID"""
        return self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()

    def get_group_by_name(self, name: str) -> Optional[RouterGroup]:
        """Get a group by name"""
        return self.db.query(RouterGroup).filter(RouterGroup.name == name).first()

    def list_groups(self, skip: int = 0, limit: int = 100) -> Tuple[List[RouterGroup], int]:
        """List all groups"""
        total = self.db.query(RouterGroup).count()
        groups = self.db.query(RouterGroup).offset(skip).limit(limit).all()
        return groups, total

    def get_group_tree(self) -> List[RouterGroup]:
        """Get groups in tree structure (only root-level groups)"""
        return self.db.query(RouterGroup).filter(RouterGroup.parent_id == None).all()

    def add_routers_to_group(self, group_id: int, router_ids: List[int]) -> Optional[RouterGroup]:
        """Add routers to a group"""
        group = self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
        if not group:
            return None

        routers = self.db.query(Router).filter(Router.id.in_(router_ids)).all()
        for router in routers:
            if router not in group.routers:
                group.routers.append(router)

        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Added {len(routers)} routers to group {group.name}")
        return group

    def remove_routers_from_group(self, group_id: int, router_ids: List[int]) -> Optional[RouterGroup]:
        """Remove routers from a group"""
        group = self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
        if not group:
            return None

        routers = self.db.query(Router).filter(Router.id.in_(router_ids)).all()
        for router in routers:
            if router in group.routers:
                group.routers.remove(router)

        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Removed {len(routers)} routers from group {group.name}")
        return group

    def get_routers_in_group(self, group_id: int, include_children: bool = False) -> List[Router]:
        """Get all routers in a group"""
        group = self.db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
        if not group:
            return []

        routers = list(group.routers)

        if include_children:
            for child in group.children:
                routers.extend(self.get_routers_in_group(child.id, include_children=True))

        return list(set(routers))  # Remove duplicates

    def get_router_groups(self, router_id: int) -> List[RouterGroup]:
        """Get all groups a router belongs to"""
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return []
        return list(router.groups)

    def get_group_router_count(self, group_id: int, include_children: bool = False) -> int:
        """Get count of routers in a group"""
        routers = self.get_routers_in_group(group_id, include_children)
        return len(routers)

    def _would_create_cycle(self, group_id: int, parent_id: int) -> bool:
        """Check if setting parent_id would create a circular reference"""
        current_id = parent_id
        visited = {group_id}

        while current_id:
            if current_id in visited:
                return True
            visited.add(current_id)

            parent = self.db.query(RouterGroup).filter(RouterGroup.id == current_id).first()
            current_id = parent.parent_id if parent else None

        return False

    def search_groups(self, query: str) -> List[RouterGroup]:
        """Search groups by name or description"""
        search_term = f"%{query}%"
        return self.db.query(RouterGroup).filter(
            (RouterGroup.name.ilike(search_term)) |
            (RouterGroup.description.ilike(search_term))
        ).all()
