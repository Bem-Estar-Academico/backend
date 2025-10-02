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

    @classmethod
    def from_model_with_url(cls, document_model):
        from app.core.s3_manager import s3_manager

        return cls(
            id=document_model.id,
            notice_id=document_model.notice_id,
            name=document_model.name,
            file_key=document_model.file_key,
            file_type=document_model.file_type,
            file_size=document_model.file_size,
            uploaded_at=document_model.uploaded_at,
            file_url=s3_manager.generate_presigned_download_url(
                document_model.file_key
            ),
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
    documents: List[DocumentWithUrl] = []
    team_members: List[NoticeTeamMember] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, notice_model):
        return cls(
            id=notice_model.id,
            title=notice_model.title,
            notice_number=notice_model.notice_number,
            year=notice_model.year,
            start_date=notice_model.start_date,
            end_date=notice_model.end_date,
            responsible_agency=notice_model.responsible_agency,
            description=notice_model.description,
            food_allowance=notice_model.food_allowance,
            housing_allowance=notice_model.housing_allowance,
            daycare_allowance=notice_model.daycare_allowance,
            graduation_scholarship=notice_model.graduation_scholarship,
            created_at=notice_model.created_at,
            updated_at=notice_model.updated_at,
            documents=[
                DocumentWithUrl.from_model_with_url(doc)
                for doc in notice_model.documents
            ],
            team_members=[
                NoticeTeamMember.from_model(team) for team in notice_model.team_members
            ],
        )
