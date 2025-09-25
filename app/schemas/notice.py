from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Nome do documento"
    )
    file_url: str = Field(
        ..., min_length=1, max_length=512, description="URL do arquivo"
    )
    file_type: Optional[str] = Field(None, max_length=50, description="Tipo do arquivo")
    file_size: Optional[int] = Field(None, ge=0, description="Tamanho em bytes")


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: int
    notice_id: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class NoticeTeamBase(BaseModel):
    user_id: int
    role: str = Field(..., description="COORDINATOR ou SOCIAL_WORKER")


class NoticeTeamCreate(NoticeTeamBase):
    pass


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

    auxilio_alimentacao: bool = False
    auxilio_moradia: bool = False
    auxilio_creche: bool = False
    bolsa_pro_graduando: bool = False


class NoticeCreate(NoticeBase):
    documents: Optional[List[DocumentCreate]] = []
    team_members: Optional[List[NoticeTeamCreate]] = []


class NoticeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    notice_number: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=2020, le=2030)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    responsible_agency: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)

    auxilio_alimentacao: Optional[bool] = None
    auxilio_moradia: Optional[bool] = None
    auxilio_creche: Optional[bool] = None
    bolsa_pro_graduando: Optional[bool] = None


class Notice(NoticeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    documents: List[Document] = []
    team_members: List[NoticeTeam] = []

    model_config = {"from_attributes": True}
