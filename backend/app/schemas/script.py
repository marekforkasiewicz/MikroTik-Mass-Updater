"""Script schemas"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScriptVariable(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(default="string", pattern="^(string|number|boolean)$")
    default: Optional[Any] = None
    required: bool = False
    description: Optional[str] = None


class ScriptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    script_type: str = Field(default="routeros", pattern="^(routeros|ssh)$")
    content: str = Field(..., min_length=1)
    variables: List[ScriptVariable] = Field(default_factory=list)

    timeout: int = Field(default=60, ge=1, le=3600)
    requires_reboot: bool = False
    dangerous: bool = False

    category: str = Field(default="general", max_length=50)
    tags: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default=["admin", "operator"])
    enabled: bool = True


class ScriptCreate(ScriptBase):
    pass


class ScriptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    variables: Optional[List[ScriptVariable]] = None

    timeout: Optional[int] = Field(None, ge=1, le=3600)
    requires_reboot: Optional[bool] = None
    dangerous: Optional[bool] = None

    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    enabled: Optional[bool] = None


class ScriptResponse(ScriptBase):
    id: int
    validated: bool = False
    execution_count: int = 0
    last_executed: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScriptListResponse(BaseModel):
    items: List[ScriptResponse]
    total: int


# Execution schemas
class ScriptExecuteRequest(BaseModel):
    router_ids: List[int]
    variables: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class ScriptExecutionResponse(BaseModel):
    id: int
    script_id: int
    router_id: int
    variables_used: Dict[str, Any] = Field(default_factory=dict)
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    output: Optional[str] = None
    error_message: Optional[str] = None
    return_value: Optional[Any] = None
    executed_by: Optional[int] = None

    class Config:
        from_attributes = True


class ScriptExecutionListResponse(BaseModel):
    items: List[ScriptExecutionResponse]
    total: int


class BulkScriptExecuteRequest(BaseModel):
    router_ids: List[int]
    variables: Dict[str, Any] = Field(default_factory=dict)


class BulkScriptExecuteResponse(BaseModel):
    task_id: str
    message: str


class ValidateScriptRequest(BaseModel):
    content: str
    script_type: str = Field(default="routeros", pattern="^(routeros|ssh)$")


class ValidateScriptResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
