"""Router group schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: str = Field(default="#3498db", pattern="^#[0-9a-fA-F]{6}$")
    icon: str = Field(default="folder", max_length=50)
    parent_id: Optional[int] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[int] = None


class GroupResponse(GroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    router_count: int = 0

    class Config:
        from_attributes = True


class GroupWithRoutersResponse(GroupResponse):
    router_ids: List[int] = []


class GroupTreeResponse(GroupResponse):
    children: List["GroupTreeResponse"] = []

    class Config:
        from_attributes = True


# Allow recursive reference
GroupTreeResponse.model_rebuild()


class GroupListResponse(BaseModel):
    items: List[GroupResponse]
    total: int


class AddRoutersToGroupRequest(BaseModel):
    router_ids: List[int]


class RemoveRoutersFromGroupRequest(BaseModel):
    router_ids: List[int]
