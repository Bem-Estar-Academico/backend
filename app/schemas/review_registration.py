"""
Schemas for validating and serializing review registration data.

This module defines Pydantic models used to validate and serialize
data related to social worker reviews of student registrations.
"""

from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from app.schemas.user import UserInfo
from app.schemas.student_registration import StudentRegistrationResponse 
from app.models.review import ReviewRegistrationModel

class ReviewRegistrationBase(BaseModel):
    """
    Base schema for a review of a student registration.

    Attributes:
        review (dict[str, Any]): Structured JSON data containing the review content.
        ivs (float): Income Verification Score (IVS) or other numerical evaluation metric.
    """
    review: dict[str, Any] = Field(..., description="Conteúdo da avaliação em formato JSON")
    ivs: float = Field(..., ge=0, description="Índice de vulnerabilidade econômica (IVS)")


class ReviewRegistrationCreate(ReviewRegistrationBase):
    """
    Schema for creating a new review registration record.
    We need the IDs to link the review upon creation.
    """
    pass


class ReviewRegistrationUpdate(BaseModel):
    """
    Schema for updating an existing review registration.

    All fields are optional to allow partial updates.
    """
    review: Dict[str, Any] | None = Field(None, description="Conteúdo atualizado da avaliação em formato JSON")
    ivs: float | None = Field(None, ge=0, description="(IVS) atualizado")


class ReviewRegistrationResponse(ReviewRegistrationBase):
    """
    Schema representing a basic review registration record with metadata and FKs.
    """
    id: int
    social_worker_id: int
    student_registration_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewRegistrationResponseWithDetails(ReviewRegistrationResponse):
    """
    Schema representing a detailed review record, embedding the related
    Social Worker and Student Registration information.
    """
    social_worker: UserInfo = Field(
        ..., description="Informações do assistente social que realizou a revisão."
    )
    student_registration: StudentRegistrationResponse = Field(
        ..., description="Informações da inscrição de estudante revisada."
    )
    @classmethod
    def from_model(cls, review_model: ReviewRegistrationModel) -> "ReviewRegistrationResponseWithDetails":
        """
        Factory method to create the detailed schema instance from a SQLAlchemy model instance.
        """
        ivs_value = float(review_model.ivs) if isinstance(review_model.ivs, (Decimal, str)) else review_model.ivs
        return cls(
            id=review_model.id,
            social_worker_id=review_model.social_worker_id,
            student_registration_id=review_model.student_registration_id,
            review=review_model.review,
            ivs=ivs_value,
            created_at=review_model.created_at,
            updated_at=review_model.updated_at,
            social_worker=UserInfo.model_validate(review_model.social_worker),
            student_registration=StudentRegistrationResponse.model_validate(review_model.student_registration),
        )