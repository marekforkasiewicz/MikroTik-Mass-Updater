"""Pydantic schemas for Update operations"""

from typing import Optional, List
from pydantic import BaseModel, Field
from ..core.enums import UpdateTree


class UpdateConfig(BaseModel):
    """Configuration for update operation"""
    router_ids: List[int] = Field(..., description="List of router IDs to update")
    update_tree: UpdateTree = Field(default=UpdateTree.STABLE, description="Update tree")
    auto_change_tree: bool = Field(default=False, description="Auto-change tree via SSH")
    upgrade_firmware: bool = Field(default=False, description="Also upgrade firmware")
    cloud_backup: bool = Field(default=False, description="Perform cloud backup first")
    cloud_password: Optional[str] = Field(None, description="Cloud backup password")
    dry_run: bool = Field(default=False, description="Dry run mode (no actual changes)")
    timeout: int = Field(default=30, ge=1, le=120, description="Connection timeout in seconds")
    threads: int = Field(default=5, ge=1, le=50, description="Number of concurrent threads")
    generate_report: bool = Field(default=True, description="Generate report after update")


class UpdateResult(BaseModel):
    """Result of an update operation for a single router"""
    router_id: int
    ip: str
    identity: Optional[str] = None
    success: bool = False
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    firmware_upgraded: bool = False
    backup_created: bool = False
    tree_changed: bool = False
    rebooted: bool = False
    error: Optional[str] = None


class UpdateSummary(BaseModel):
    """Summary of update operation"""
    total: int
    successful: int
    failed: int
    skipped: int
    results: List[UpdateResult]
