"""Schemas for student registration."""

from datetime import datetime
from app.schemas.user import UserInfo
from pydantic import BaseModel, Field
from app.schemas.notice import NoticeInfo
from typing import Optional, Any, Dict, List
from app.models.notice import RegistrationStatus, StudentRegistration


class StudentRegistrationBase(BaseModel):
    """
    Base schema for student registration data.

    This schema contains fields that are common during the registration process,
    such as general observations or answers to registration questions.

    Attributes:
        answer (Optional[Dict[str, Any]]): Observations or a dictionary containing
                                           the student's answers to registration-specific questions.
    """
    answer: Optional[Dict[str, Any]] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationUpdate(BaseModel):
    """
    Schema for updating the status or observations of a student registration.

    Attributes:
        status (Optional[RegistrationStatus]): The new status of the registration
                                              (e.g., PENDENTE, APROVADO, REPROVADO).
        answer (Optional[Dict[str, Any]]): Updated observations or a dictionary
                                           with answers (e.g., notes from a social worker).
    """
    status: Optional[RegistrationStatus] = Field(
        None, description="Status da inscrição"
    )
    answer: Optional[Dict[str, Any]] = Field(None, description="Observações sobre a inscrição")


class StudentRegistrationResponse(StudentRegistrationBase):
    """
    Schema for retrieving a basic student registration record.

    Includes key identifiers, status, and timestamps.

    Attributes:
        id (int): The unique identifier of the registration.
        student_id (int): The ID of the student who submitted the registration.
        notice_id (int): The ID of the notice (edital) the student is applying to.
        status (RegistrationStatus): The current status of the registration.
        registration_date (datetime): The original date and time the registration was submitted.
        created_at (datetime): The timestamp when the record was created in the database.
        updated_at (datetime): The timestamp when the record was last updated.
    """
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
    """
    Schema for retrieving a student registration with embedded relational details.

    Extends `StudentRegistrationResponse` by including the student's and notice's
    information, plus a document count.

    Attributes:
        student (UserInfo): Embedded detailed information about the registered student.
        notice (NoticeInfo): Embedded basic information about the notice (edital).
        documents_count (int): The total number of documents uploaded by the student for this registration.
    """
    student: UserInfo
    notice: NoticeInfo
    documents_count: int = Field(
        ..., description="Quantidade de documentos enviados pelo estudante"
    )

    @classmethod
    def from_model(cls, registration_model: StudentRegistration) -> "StudentRegistrationWithDetails":
        """
        Factory method to create the schema instance from a SQLAlchemy model instance.
        It handles the conversion of related models (`student` and `notice`) to their
        respective Pydantic schemas.
        """
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
    """
    Schema for a paginated or bulk list of student registrations with details.

    Attributes:
        registrations (List[StudentRegistrationWithDetails]): A list of detailed registration records.
        total (int): The total count of registrations found (useful for pagination).
    """
    registrations: List[StudentRegistrationWithDetails]
    total: int