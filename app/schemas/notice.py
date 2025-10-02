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
    file_url: str = Field(
        ..., description="URL assinada do arquivo (válida por tempo limitado)"
    )
    file_key: str = Field(..., description="Chave do arquivo no S3")
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class NoticeTeamBase(BaseModel):
    user_id: int
    role: str = Field(..., description="COORDINATOR ou SOCIAL_WORKER")


class NoticeTeamCreate(NoticeTeamBase):
    pass


class NoticeTeamMember(BaseModel):
    id: int
    user_id: int
    role: str
    assigned_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = {"from_attributes": True}


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
    start_date: datetime
    end_date: datetime
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
    year: Optional[int] = Field(None, ge=2020, le=2030)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
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
    documents: List[Document] = []
    team_members: List[NoticeTeamMember] = []

    model_config = {"from_attributes": True}
