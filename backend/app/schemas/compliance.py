"""Pydantic schemas for Compliance checking"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


# ============== Compliance Rule Schemas ==============

class ComplianceRuleSchema(BaseModel):
    """Schema for a compliance rule"""
    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    type: str = Field(..., description="Rule type: contains, not_contains, regex_match, regex_not_match, setting")
    pattern: Optional[str] = Field(None, description="Pattern to match (for contains/regex types)")
    path: Optional[str] = Field(None, description="Config path (for setting type)")
    setting: Optional[str] = Field(None, description="Setting name (for setting type)")
    expected: Optional[str] = Field(None, description="Expected value (for setting type)")
    severity: str = Field(default="warning", description="Severity: info, warning, critical")
    description: Optional[str] = Field(None, description="Rule description")


# ============== Compliance Baseline Schemas ==============

class BaselineBase(BaseModel):
    """Base baseline schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Baseline name")
    description: Optional[str] = Field(None, description="Baseline description")
    rules: List[ComplianceRuleSchema] = Field(default_factory=list, description="Compliance rules")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    is_active: bool = Field(default=True, description="Whether baseline is active")


class BaselineCreate(BaselineBase):
    """Schema for creating a baseline"""
    pass


class BaselineUpdate(BaseModel):
    """Schema for updating a baseline"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rules: Optional[List[ComplianceRuleSchema]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BaselineResponse(BaselineBase):
    """Schema for baseline response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BaselineListResponse(BaseModel):
    """Response with list of baselines"""
    items: List[BaselineResponse]
    total: int


# ============== Compliance Check Schemas ==============

class RuleResultSchema(BaseModel):
    """Schema for a single rule check result"""
    name: str
    type: str
    pattern: Optional[str] = None
    severity: str
    description: Optional[str] = None
    status: str = Field(..., description="compliant, non_compliant, error")
    details: Optional[str] = None


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check"""
    router_ids: List[int] = Field(..., min_length=1, description="Router IDs to check")
    baseline_id: int = Field(..., description="Baseline ID to check against")


class ComplianceCheckResponse(BaseModel):
    """Schema for compliance check response"""
    id: int
    router_id: int
    baseline_id: int
    status: str = Field(..., description="compliant, partial, non_compliant, error")
    compliant_rules: int = 0
    non_compliant_rules: int = 0
    results: List[RuleResultSchema] = Field(default_factory=list)
    error_message: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


class ComplianceCheckDetailResponse(ComplianceCheckResponse):
    """Detailed compliance check response with config snapshot"""
    config_snapshot: Optional[str] = None


class ComplianceCheckListResponse(BaseModel):
    """Response with list of compliance checks"""
    items: List[ComplianceCheckResponse]
    total: int


class ComplianceSummaryResponse(BaseModel):
    """Summary of compliance across routers"""
    total_routers: int
    compliant: int
    partial: int
    non_compliant: int
    error: int
    compliance_rate: float


# ============== Config Export/Diff Schemas ==============

class ConfigExportResponse(BaseModel):
    """Response for config export"""
    router_id: int
    router_ip: str
    router_identity: Optional[str] = None
    config: Optional[str] = None
    error: Optional[str] = None
    exported_at: datetime = Field(default_factory=datetime.utcnow)


class ConfigDiffRequest(BaseModel):
    """Request for config diff"""
    router_a_id: Optional[int] = Field(None, description="First router ID (for router comparison)")
    router_b_id: Optional[int] = Field(None, description="Second router ID (for router comparison)")
    config_a: Optional[str] = Field(None, description="First config (for direct comparison)")
    config_b: Optional[str] = Field(None, description="Second config (for direct comparison)")
    label_a: str = Field(default="Config A", description="Label for first config")
    label_b: str = Field(default="Config B", description="Label for second config")
    hide_sensitive: bool = Field(default=True, description="Hide sensitive data when exporting")


class ConfigDiffResponse(BaseModel):
    """Response for config diff"""
    unified_diff: str = Field(..., description="Unified diff output")
    added_lines: int
    removed_lines: int
    has_changes: bool
    label_a: str
    label_b: str
    error: Optional[str] = None
