from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NoticeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    important_dates: Optional[Dict[str, Any]] = None
    start_date: datetime
    end_date: datetime
    document_url: Optional[str] = Field(None, max_length=512)


class NoticeCreate(NoticeBase):
    coordinator_id: int


class NoticeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    important_dates: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    document_url: Optional[str] = Field(None, max_length=512)


class Notice(NoticeBase):
    id: int
    coordinator_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
