"""Pydantic schemas for Task"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from ..core.enums import TaskType, TaskStatus, UpdateTree


class TaskConfig(BaseModel):
    """Configuration for a task"""
    router_ids: Optional[List[int]] = Field(None, description="List of router IDs to process")
    update_tree: Optional[UpdateTree] = Field(None, description="Update tree to use")
    auto_change_tree: bool = Field(default=False, description="Auto-change update tree via SSH")
    upgrade_firmware: bool = Field(default=False, description="Upgrade firmware")
    cloud_backup: bool = Field(default=False, description="Perform cloud backup")
    cloud_password: Optional[str] = Field(None, description="Cloud backup password")
    dry_run: bool = Field(default=False, description="Dry run mode")
    threads: int = Field(default=5, description="Number of concurrent threads")
    timeout: int = Field(default=30, description="Connection timeout in seconds")


class TaskCreate(BaseModel):
    """Schema for creating a task"""
    type: TaskType
    config: Optional[TaskConfig] = None


class TaskResponse(BaseModel):
    """Schema for task response"""
    id: str
    type: str
    status: str
    config: Optional[Dict[str, Any]] = None
    progress: int = 0
    total: int = 0
    current_item: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def progress_percent(self) -> int:
        if self.total == 0:
            return 0
        return int((self.progress / self.total) * 100)


class TaskProgress(BaseModel):
    """Schema for task progress updates (WebSocket)"""
    task_id: str
    status: str
    progress: int
    total: int
    current_item: Optional[str] = None
    message: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response with list of tasks"""
    tasks: List[TaskResponse]
    total: int
