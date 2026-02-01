"""Backup and rollback schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Backup schemas
class BackupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    backup_type: str = Field(..., pattern="^(config|full|export|cloud)$")


class BackupCreate(BackupBase):
    router_id: int
    includes_passwords: bool = False
    encryption_type: Optional[str] = Field(None, pattern="^(none|aes256)$")
    keep_forever: bool = False


class BackupResponse(BackupBase):
    id: int
    router_id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    cloud_name: Optional[str] = None
    router_version: Optional[str] = None
    router_model: Optional[str] = None
    router_identity: Optional[str] = None
    includes_passwords: bool = False
    encryption_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    is_auto: bool = False
    keep_forever: bool = False
    expires_at: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class BackupListResponse(BaseModel):
    items: List[BackupResponse]
    total: int


class BackupDownloadResponse(BaseModel):
    url: str
    filename: str
    expires_at: datetime


# Rollback schemas
class RollbackCreate(BaseModel):
    router_id: int
    backup_id: Optional[int] = None
    rollback_type: str = Field(..., pattern="^(restore|downgrade|config_restore)$")
    reason: Optional[str] = None
    target_version: Optional[str] = None


class RollbackResponse(BaseModel):
    id: int
    router_id: int
    backup_id: Optional[int] = None
    rollback_type: str
    reason: Optional[str] = None
    previous_version: Optional[str] = None
    previous_config_hash: Optional[str] = None
    target_version: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    initiated_by: Optional[int] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    reboot_required: bool = False
    reboot_completed: bool = False

    class Config:
        from_attributes = True


class RollbackListResponse(BaseModel):
    items: List[RollbackResponse]
    total: int


# Bulk backup request
class BulkBackupRequest(BaseModel):
    router_ids: List[int]
    backup_type: str = Field(default="config", pattern="^(config|full|export|cloud)$")
    includes_passwords: bool = False


class BulkBackupResponse(BaseModel):
    task_id: str
    message: str
