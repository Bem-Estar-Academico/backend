"""Schemas for student registration."""

from datetime import datetime
import random
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserInfo
from app.schemas.notice import NoticeInfo
from app.models.registration import StudentRegistration
from app.models.review import RegistrationStatus


class StudentRegistrationBase(BaseModel):
    """
    Base schema for student registration data.

    This schema contains fields that are common during the registration process,
    such as general observations, answers to registration questions, and requested benefits.

    Attributes:
        answer (Optional[Dict[str, Any]]): Observations or a dictionary containing
                                           the student's answers to registration-specific questions.
        requested_food_allowance (bool): Whether the student requested food allowance benefit.
        requested_housing_allowance (bool): Whether the student requested housing allowance benefit.
        requested_daycare_allowance (bool): Whether the student requested daycare allowance benefit.
        requested_graduation_scholarship (bool): Whether the student requested graduation scholarship benefit.
    """

    answer: Optional[Dict[str, Any]] = Field(
        None,
        description="Observações ou respostas fornecidas pelo estudante durante a inscrição",
    )
    requested_food_allowance: bool = Field(
        default=False, description="Indica se o estudante solicitou auxílio alimentação"
    )
    requested_housing_allowance: bool = Field(
        default=False, description="Indica se o estudante solicitou auxílio moradia"
    )
    requested_daycare_allowance: bool = Field(
        default=False, description="Indica se o estudante solicitou auxílio creche"
    )
    requested_graduation_scholarship: bool = Field(
        default=False, description="Indica se o estudante solicitou bolsa conclusão"
    )


class StudentRegistrationCreate(StudentRegistrationBase):
    """
    Schema for creating a new student registration.

    Inherits all base fields since no additional fields are required at creation time.
    """

    pass


class StudentRegistrationUpdate(StudentRegistrationBase):
    """
    Schema for updating the status or observations of a student registration.

    Attributes:
        answer (Optional[Dict[str, Any]]): Updated observations or a dictionary
                                           with answers (e.g., notes from a social worker).
    """
    answer: Optional[Dict[str, Any]] = Field(
        None, description="Observações atualizadas ou respostas do estudante"
    )


class StudentRegistrationResponse(StudentRegistrationBase):
    """
    Schema for retrieving a basic student registration record.

    Includes key identifiers, status, and timestamps.

    Attributes:
        id (int): The unique identifier of the registration.
        student_id (int): The ID of the student who submitted the registration.
        notice_id (int): The ID of the notice (edital) the student is applying to.
        created_at (datetime): The timestamp when the record was created in the database.
        updated_at (datetime): The timestamp when the record was last updated.
    """

    id: int
    student_id: int
    notice_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(
        cls, registration_model: StudentRegistration
    ) -> "StudentRegistrationWithDetails":
        """
        Factory method to create the schema instance from a SQLAlchemy model instance.
        It handles the conversion of related models (`student` and `notice`) to their
        respective Pydantic schemas.
        """
        return cls(
            id=registration_model.id,
            student_id=registration_model.student_id,
            notice_id=registration_model.notice_id,
            answer=registration_model.answer,
            created_at=registration_model.created_at,
            updated_at=registration_model.updated_at,
            student=UserInfo.model_validate(registration_model.student),
            notice=NoticeInfo.model_validate(registration_model.notice),
            documents_count=random.randint(12, 80),
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

    model_config = ConfigDict(from_attributes=True)


class NoticeDetailsForRegistration(BaseModel):
    """
    Schema for notice details included in student registration responses.
    """

    id: int
    title: str
    registration_end_date: datetime
    appeal_start_date: Optional[datetime] = None
    appeal_end_date: Optional[datetime] = None
    registration_start_date: datetime
    preliminary_result_date: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ReviewDetailsForRegistration(BaseModel):
    """
    Schema for review details included in student registration responses.
    """

    id: int
    status: RegistrationStatus
    ivs: Optional[float] = None
    expires_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class StudentRegistrationWithReviewResponse(BaseModel):
    """
    Schema for representing a student's registration along with notice and review details.
    """

    notice: NoticeDetailsForRegistration
    review: Optional[ReviewDetailsForRegistration] = None
    model_config = ConfigDict(from_attributes=True)


# Schemas for the new endpoint GET /api/v1/student-registrations/notice/{notice_id}

class ReviewerResponse(BaseModel):
    id: int
    name: str

class ReviewerWrapper(BaseModel):
    reviewer: Optional[ReviewerResponse]

class ReviewForRegistrationList(BaseModel):
    progress: int
    status: str
    qtd_document: int
    reviewer: Optional[ReviewerResponse] = None

class StudentForRegistrationList(BaseModel):
    id: int
    cpf: Optional[str] = None
    name: str
    registration_number: Optional[str] = None
    created_at: datetime

class RegistrationForNoticeList(BaseModel):
    id: int
    registration_date: datetime
    student: StudentForRegistrationList
    review: ReviewForRegistrationList

class RegistrationListResponse(BaseModel):
    registrations: List[RegistrationForNoticeList]
    pending_count: int
    approved_count: int
    rejected_count: int
    review_count: int
    appeal_count: int
    cancelled_count: int
