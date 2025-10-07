from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Nome do documento"
    )
    file_type: Optional[str] = Field(None, max_length=50, description="Tipo do arquivo")
    file_size: Optional[int] = Field(None, ge=0, description="Tamanho em bytes")


class DocumentCreate(DocumentBase):
    """Schema for creating a document - file will be uploaded directly"""

    pass


class Document(DocumentBase):
    id: int
    notice_id: int
    file_key: str = Field(..., description="Chave do arquivo no S3")
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentWithUrl(Document):
    file_url: str = Field(
        ..., description="URL assinada do arquivo (válida por tempo limitado)"
    )


class NoticeTeamBase(BaseModel):
    user_id: int
    role: str = Field(..., description="COORDINATOR ou SOCIAL_WORKER")


class NoticeTeamCreate(NoticeTeamBase):
    pass


class UserInfo(BaseModel):
    id: int
    email: str
    full_name: str
    user_type: str

    model_config = {"from_attributes": True}


class NoticeTeamMember(BaseModel):
    id: int
    user_id: int
    role: str
    assigned_at: datetime
    user: UserInfo

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, team_model):
        return cls(
            id=team_model.id,
            user_id=team_model.user_id,
            role=team_model.role,
            assigned_at=team_model.assigned_at,
            user=UserInfo(
                id=team_model.user.id,
                email=team_model.user.email,
                full_name=team_model.user.full_name,
                user_type=team_model.user.user_type.value,
            ),
        )


class NoticeTeam(NoticeTeamBase):
    id: int
    notice_id: int
    assigned_at: datetime

    model_config = {"from_attributes": True}


class NoticeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    notice_number: str = Field(
        ..., min_length=1, max_length=50, description="Número do edital (ex: 05/2025)"
    )
    year: int = Field(..., ge=2000, le=3000, description="Ano de vigência")

    registration_start_date: datetime = Field(
        ..., description="Data de início das inscrições"
    )
    registration_end_date: datetime = Field(
        ..., description="Data de término das inscrições"
    )

    appeal_start_date: Optional[datetime] = Field(
        None, description="Data de início da fase de recursos"
    )
    appeal_end_date: Optional[datetime] = Field(
        None, description="Data de término da fase de recursos"
    )

    preliminary_result_date: Optional[datetime] = Field(
        None, description="Data de divulgação do resultado preliminar"
    )
    final_result_date: Optional[datetime] = Field(
        None, description="Data de divulgação do resultado final"
    )

    responsible_agency: str = Field(
        ..., min_length=1, max_length=255, description="Órgão responsável"
    )
    description: str = Field(..., min_length=1)

    food_allowance: bool = False
    housing_allowance: bool = False
    daycare_allowance: bool = False
    graduation_scholarship: bool = False


class NoticeCreate(NoticeBase): ...


class NoticeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    notice_number: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=2000, le=3000)

    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None

    appeal_start_date: Optional[datetime] = None
    appeal_end_date: Optional[datetime] = None

    preliminary_result_date: Optional[datetime] = None
    final_result_date: Optional[datetime] = None

    responsible_agency: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)

    food_allowance: Optional[bool] = None
    housing_allowance: Optional[bool] = None
    daycare_allowance: Optional[bool] = None
    graduation_scholarship: Optional[bool] = None


class Notice(NoticeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentWithUrl] = Field(default_factory=list)
    team_members: List[NoticeTeamMember] = Field(default_factory=list)

    model_config = {"from_attributes": True}
