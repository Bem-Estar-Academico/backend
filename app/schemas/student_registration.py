"""Schemas for student registration."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.notice import RegistrationStatus
from app.schemas.notice import NoticeInfo
from app.schemas.user import UserInfo


class StudentRegistrationBase(BaseModel):
    notes: Optional[str] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationCreate(StudentRegistrationBase):
    notice_id: int = Field(..., description="ID do edital")
    status: RegistrationStatus = Field(
        RegistrationStatus.PENDING, description="Status da inscrição"
    )
    
class StudentRegistrationUpdate(BaseModel):
    status: Optional[RegistrationStatus] = Field(
        None, description="Status da inscrição"
    )
    notes: Optional[str] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationResponse(StudentRegistrationBase):
    id: int
    student_id: int
    notice_id: int
    status: RegistrationStatus
    registration_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentRegistrationWithDetails(StudentRegistrationResponse):
    student: UserInfo
    notice: NoticeInfo


class StudentRegistrationList(BaseModel):
    registrations: list[StudentRegistrationWithDetails]
    total: int
