"""Pydantic schemas for Config Templates and Device Profiles"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


# ============== Template Variable Schema ==============

class TemplateVariable(BaseModel):
    """Schema for template variable definition"""
    name: str = Field(..., min_length=1, max_length=50, description="Variable name")
    type: str = Field(default="string", description="Variable type: string, integer, boolean, list")
    default: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(default=False, description="Whether variable is required")
    description: Optional[str] = Field(None, description="Variable description")


# ============== Config Template Schemas ==============

class TemplateBase(BaseModel):
    """Base template schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(default="general", description="Template category")
    content: str = Field(..., min_length=1, description="Jinja2 template content")
    variables: List[TemplateVariable] = Field(default_factory=list, description="Template variables")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    is_active: bool = Field(default=True, description="Whether template is active")


class TemplateCreate(TemplateBase):
    """Schema for creating a template"""
    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    variables: Optional[List[TemplateVariable]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    """Schema for template response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response with list of templates"""
    items: List[TemplateResponse]
    total: int


# ============== Template Preview/Validation Schemas ==============

class TemplatePreviewRequest(BaseModel):
    """Request for template preview"""
    router_id: Optional[int] = Field(None, description="Router ID to use for preview")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables to use in preview")


class TemplatePreviewResponse(BaseModel):
    """Response for template preview"""
    rendered: str = Field(..., description="Rendered template content")
    variables_used: Dict[str, Any] = Field(default_factory=dict, description="Variables used in rendering")


class TemplateValidateRequest(BaseModel):
    """Request for template validation"""
    content: str = Field(..., description="Template content to validate")


class TemplateValidateResponse(BaseModel):
    """Response for template validation"""
    valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# ============== Template Deployment Schemas ==============

class TemplateDeployRequest(BaseModel):
    """Request for deploying a template"""
    router_ids: List[int] = Field(..., min_length=1, description="Router IDs to deploy to")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables for deployment")
    dry_run: bool = Field(default=False, description="Preview without executing")
    backup_before: bool = Field(default=True, description="Create backup before deployment")


class TemplateDeployRouterResult(BaseModel):
    """Result of deployment to a single router"""
    router_id: int
    router_ip: str
    router_identity: Optional[str] = None
    status: str = Field(..., description="pending, running, completed, failed")
    rendered_content: Optional[str] = None
    error: Optional[str] = None
    backup_id: Optional[int] = None


class TemplateDeployResponse(BaseModel):
    """Response for template deployment"""
    deployment_id: Optional[int] = None
    template_id: int
    total_routers: int
    dry_run: bool
    results: List[TemplateDeployRouterResult] = Field(default_factory=list)
    task_id: Optional[str] = Field(None, description="Task ID for tracking progress (non-dry-run only)")


# ============== Device Profile Schemas ==============

class DeviceFilterSchema(BaseModel):
    """Schema for device matching filter"""
    model: List[str] = Field(default_factory=list, description="Model patterns (glob)")
    architecture: List[str] = Field(default_factory=list, description="Architecture types")


class ProfileBase(BaseModel):
    """Base device profile schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    description: Optional[str] = Field(None, description="Profile description")
    device_filter: DeviceFilterSchema = Field(default_factory=DeviceFilterSchema, description="Device matching filter")
    execution_order: List[int] = Field(default_factory=list, description="Template execution order")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Profile-level variable defaults")
    is_active: bool = Field(default=True, description="Whether profile is active")


class ProfileCreate(ProfileBase):
    """Schema for creating a profile"""
    template_ids: List[int] = Field(default_factory=list, description="Template IDs to associate")


class ProfileUpdate(BaseModel):
    """Schema for updating a profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    device_filter: Optional[DeviceFilterSchema] = None
    execution_order: Optional[List[int]] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    template_ids: Optional[List[int]] = None


class ProfileResponse(ProfileBase):
    """Schema for profile response"""
    id: int
    template_ids: List[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileListResponse(BaseModel):
    """Response with list of profiles"""
    items: List[ProfileResponse]
    total: int


# ============== Template Deployment Record Schemas ==============

class DeploymentResponse(BaseModel):
    """Schema for deployment record response"""
    id: int
    template_id: int
    router_id: int
    rendered_content: Optional[str] = None
    variables_used: Dict[str, Any] = Field(default_factory=dict)
    status: str
    error_message: Optional[str] = None
    backup_id: Optional[int] = None
    deployed_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    """Response with list of deployments"""
    items: List[DeploymentResponse]
    total: int
