"""Pydantic models for IVS data."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.notice import Notice
from app.schemas.user import UserInfo


class IVSData(BaseModel):
    """Schema for returning IVS data."""

    student: UserInfo = Field(..., description="Full student object.")
    notice: Notice = Field(..., description="Full notice object.")
    ivs_score: float = Field(..., description="The calculated IVS score.")
    expiration_date: datetime = Field(
        ..., description="The expiration date of the IVS."
    )

    class Config:
        from_attributes = True
