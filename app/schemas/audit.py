"""
Schemas for audit log data.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.models.audit import AuditAction, AuditEntityType
from app.schemas.user import UserInfo


class AuditLogBase(BaseModel):
    """Base schema for audit log."""
    
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: int
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""

    user_id: int


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response."""

    id: int
    user: UserInfo
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
