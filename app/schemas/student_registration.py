"""Schemas for student registration."""

from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field

from app.models.notice import RegistrationStatus, StudentRegistration
from app.schemas.notice import NoticeInfo
from app.schemas.user import UserInfo


class StudentRegistrationBase(BaseModel):
    answer: Optional[Dict[str, Any]] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationUpdate(BaseModel):
    status: Optional[RegistrationStatus] = Field(
        None, description="Status da inscrição"
    )
    answer: Optional[Dict[str, Any]] = Field(None, description="Observações sobre a inscrição")


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
    documents_count: int = Field(
        ..., description="Quantidade de documentos enviados pelo estudante"
    )

    @classmethod
    def from_model(cls, registration_model: StudentRegistration) -> "StudentRegistrationWithDetails":
        return cls(
            id=registration_model.id,
            student_id=registration_model.student_id,
            notice_id=registration_model.notice_id,
            status=registration_model.status,
            registration_date=registration_model.registration_date,
            answer=registration_model.answer,
            created_at=registration_model.created_at,
            updated_at=registration_model.updated_at,
            student=UserInfo.model_validate(registration_model.student),
            notice=NoticeInfo.model_validate(registration_model.notice),
            # TODO: Implementar contagem real de documentos por estudante
            # Atualmente usando valor mockado fixo
            documents_count=30,  # Valor mockado por enquanto
        )


class StudentRegistrationList(BaseModel):
    registrations: list[StudentRegistrationWithDetails]
    total: int
