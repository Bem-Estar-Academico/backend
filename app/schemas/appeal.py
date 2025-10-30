"""Pydantic schemas for appeals."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

class AppealBase(BaseModel):
    """Base schema for appeal data, containing the requested documents."""
    requested_documents: Dict[str, Any] = Field(
        ...,
        description="Dicionário detalhando documentos solicitados e justificativas.",
        example={"rg_frente": "Reenvie a foto com melhor iluminação.", "comprovante_residencia": "Documento ilegível."}
    )


class AppealCreate(AppealBase):
    """Schema for creating a new appeal. Inherits requested_documents."""
    pass


class AppealUpdate(BaseModel):
    """
    Schema for updating an appeal. Only requested_documents can be updated.
    Fields are optional.
    """
    requested_documents: Optional[Dict[str, Any]] = Field(
        None,
        description="Dicionário atualizado de documentos solicitados."
    )


class AppealResponse(AppealBase):
    """Schema for representing an appeal with its ID."""

    id: int
    created_at: datetime
    updated_at: datetime
    review_registration_id: int

    model_config = ConfigDict(from_attributes=True)