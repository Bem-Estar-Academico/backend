"""
Schemas for validating and serializing review registration data.

This module defines Pydantic models used to validate and serialize
data related to social worker reviews of student registrations.
"""

import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.schemas.appeal import AppealResponse
from app.schemas.student_registration import StudentRegistrationResponse
from app.schemas.user import UserInfo


class ReviewRegistrationBase(BaseModel):
    """
    Base schema for a review of a student registration.

    Attributes:
        review (dict[str, Any]): Structured JSON data containing the review content.
        ivs (float): Income Verification Score (IVS) or other numerical evaluation metric.
        approved_food_allowance (Optional[bool]): Whether food allowance benefit was approved.
        approved_housing_allowance (Optional[bool]): Whether housing allowance benefit was approved.
        approved_daycare_allowance (Optional[bool]): Whether daycare allowance benefit was approved.
        approved_graduation_scholarship (Optional[bool]): Whether graduation scholarship benefit was approved.
    """

    review: Optional[dict[str, Any]] = Field(
        None, description="Conteúdo da avaliação em formato JSON"
    )
    ivs: Optional[float] = Field(
        None, ge=0, description="Índice de vulnerabilidade econômica (IVS)"
    )
    ocr_analisys: Optional[dict[str, Any]] = Field(
        None, description="Conteúdo do OCR em formato JSON"
    )
    status: RegistrationStatus = Field(..., description="Status no formato do sistema")

    approved_food_allowance: bool = Field(
        False,
        description="Indica se o auxílio alimentação foi aprovado (null se não aplicável)",
    )
    approved_housing_allowance: bool = Field(
        False,
        description="Indica se o auxílio moradia foi aprovado (null se não aplicável)",
    )
    approved_daycare_allowance: bool = Field(
        False,
        description="Indica se o auxílio creche foi aprovado (null se não aplicável)",
    )
    approved_graduation_scholarship: bool = Field(
        False,
        description="Indica se a bolsa conclusão foi aprovada (null se não aplicável)",
    )


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

    appeal: Optional[Dict[str, Any]] | None = Field(
        None, description="Conteúdo relacionado aos recursos"
    )
    review: Dict[str, Any] | None = Field(
        None, description="Conteúdo atualizado da avaliação em formato JSON"
    )
    ivs: float | None = Field(None, ge=0, description="(IVS) atualizado")
    status: RegistrationStatus | None = Field(
        None,
        description="Status só possui esses valores PENDING, APPROVED, REJECTED, CANCELLED, APPEAL, REVIEW",
    )
    approved_food_allowance: bool | None = Field(
        None,
        description="Indica se o auxílio alimentação foi aprovado (null se não aplicável)",
    )
    approved_housing_allowance: bool | None = Field(
        None,
        description="Indica se o auxílio moradia foi aprovado (null se não aplicável)",
    )
    approved_daycare_allowance: bool | None = Field(
        None,
        description="Indica se o auxílio creche foi aprovado (null se não aplicável)",
    )
    approved_graduation_scholarship: bool | None = Field(
        None,
        description="Indica se a bolsa conclusão foi aprovada (null se não aplicável)",
    )

    def calculate_ivs(self) -> float:
        "Calcular o IVS aqui"
        return random.uniform(0, 100)


class ReviewRegistrationResponse(ReviewRegistrationBase):
    """
    Schema representing a basic review registration record with metadata and FKs.
    """

    id: int
    social_worker_id: Optional[int]
    student_registration_id: int
    status: RegistrationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRegistrationResponseWithDetails(ReviewRegistrationResponse):
    """
    Schema representing a detailed review record, embedding the related
    Social Worker and Student Registration information.
    """

    social_worker: UserInfo = Field(
        ..., description="Informações do assistente social que realizou a revisão."
    )
    student_registration: "StudentRegistrationResponse" = Field(
        ..., description="Informações da inscrição de estudante revisada."
    )
    appeals: List["AppealResponse"] = Field(  # type: ignore
        default_factory=list, description="Lista de recursos associados à revisão."
    )

    @classmethod
    def from_model(
        cls, review_model: ReviewRegistrationModel
    ) -> "ReviewRegistrationResponseWithDetails":
        """
        Factory method to create the detailed schema instance from a SQLAlchemy model instance.
        """
        ivs_value = (
            float(review_model.ivs)
            if isinstance(review_model.ivs, (Decimal, str))
            else review_model.ivs
        )
        return cls(
            id=review_model.id,
            social_worker_id=review_model.social_worker_id,
            student_registration_id=review_model.student_registration_id,
            review=review_model.review,
            ivs=ivs_value,
            ocr_analisys=review_model.ocr_analisys,
            status=review_model.status,
            approved_food_allowance=review_model.approved_food_allowance,  # type: ignore
            approved_housing_allowance=review_model.approved_housing_allowance,  # type: ignore
            approved_daycare_allowance=review_model.approved_daycare_allowance,  # type: ignore
            approved_graduation_scholarship=review_model.approved_graduation_scholarship,  # type: ignore
            created_at=review_model.created_at,
            updated_at=review_model.updated_at,
            social_worker=UserInfo.model_validate(review_model.social_worker),
            student_registration=StudentRegistrationResponse.model_validate(
                review_model.student_registration
            ),
            appeals=[
                AppealResponse.model_validate(appeal)
                for appeal in review_model.appeals
            ] if review_model.appeals else [],
       
        )


ReviewRegistrationResponseWithDetails.model_rebuild()
