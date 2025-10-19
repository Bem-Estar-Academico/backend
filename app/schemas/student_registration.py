"""Schemas for student registration."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.notice import RegistrationStatus
<<<<<<< HEAD
from app.schemas.notice import NoticeInfo
=======
>>>>>>> 6a2b645527aadda9bd8a203952a213e0755124e6
from app.schemas.user import UserInfo


class NoticeInfo(BaseModel):
    id: int
    title: str
    notice_number: str
    year: int


class StudentRegistrationBase(BaseModel):
    notes: Optional[str] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationCreate(StudentRegistrationBase):
    notice_id: int = Field(..., description="ID do edital")
<<<<<<< HEAD
    status: RegistrationStatus = Field(
        RegistrationStatus.PENDING, description="Status da inscrição"
    )
    
=======


>>>>>>> 6a2b645527aadda9bd8a203952a213e0755124e6
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
<<<<<<< HEAD
=======
    documents_count: int = Field(
        ..., description="Quantidade de documentos enviados pelo estudante"
    )

    @classmethod
    def from_model(cls, registration_model) -> "StudentRegistrationWithDetails":
        return cls(
            id=registration_model.id,
            student_id=registration_model.student_id,
            notice_id=registration_model.notice_id,
            status=registration_model.status,
            registration_date=registration_model.registration_date,
            notes=registration_model.notes,
            created_at=registration_model.created_at,
            updated_at=registration_model.updated_at,
            student=UserInfo.model_validate(registration_model.student),
            notice=NoticeInfo(
                id=registration_model.notice.id,
                title=registration_model.notice.title,
                notice_number=registration_model.notice.notice_number,
                year=registration_model.notice.year,
            ),
            # TODO: Implementar contagem real de documentos por estudante
            # Atualmente usando valor mockado fixo
            documents_count=3,  # Valor mockado por enquanto
        )
>>>>>>> 6a2b645527aadda9bd8a203952a213e0755124e6


class StudentRegistrationList(BaseModel):
    registrations: list[StudentRegistrationWithDetails]
    total: int
