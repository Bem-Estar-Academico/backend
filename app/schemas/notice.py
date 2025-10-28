"""Module for defining Pydantic schemas for notice-related data."""

"""
This module defines various Pydantic schemas used for validating and serializing
data related to notices, including documents, team members, and student registrations.
It covers schemas for creating, updating, and retrieving notice information.
"""

from datetime import datetime
from typing import List, Optional, cast

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """
    Base schema for document data.

    Attributes:
        name (str): The name of the document.
        file_type (Optional[str]): The type of the file (e.g., 'application/pdf').
        file_size (Optional[int]): The size of the file in bytes.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Nome do documento"
    )
    file_type: Optional[str] = Field(None, max_length=50, description="Tipo do arquivo")
    file_size: Optional[int] = Field(None, ge=0, description="Tamanho em bytes")


class DocumentCreate(DocumentBase):
    """Schema for creating a document - file will be uploaded directly"""

    pass


class Document(DocumentBase):
    """
    Schema for a document, including its ID, associated notice ID, S3 file key, and upload timestamp.

    Attributes:
        id (int): The unique identifier of the document.
        notice_id (int): The ID of the notice this document belongs to.
        file_key (str): The key used to store the file in S3.
        uploaded_at (datetime): The timestamp when the document was uploaded.
    """

    id: int
    notice_id: int
    file_key: str = Field(..., description="Chave do arquivo no S3")
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentWithUrl(Document):
    """
    Schema for a document with an additional presigned URL for direct access.

    Extends `Document` with a `file_url` attribute.

    Attributes:
        file_url (str): A presigned URL for downloading the document, valid for a limited time.
    """

    file_url: str = Field(
        ..., description="URL assinada do arquivo (válida por tempo limitado)"
    )


class NoticeTeamBase(BaseModel):
    """
    Base schema for notice team member data.

    Attributes:
        user_id (int): The ID of the user who is a team member.
        role (str): The role of the user in the team (e.g., 'COORDINATOR', 'SOCIAL_WORKER').
    """

    user_id: int
    role: str = Field(..., description="COORDINATOR ou SOCIAL_WORKER")


class NoticeTeamCreate(NoticeTeamBase):
    """Schema for assigning a user as a team member to a notice."""

    pass


class UserInfo(BaseModel):
    """
    Schema for basic user information, typically used when embedding a user object.

    Attributes:
        id (int): The unique identifier of the user.
        email (str): The user's email address.
        full_name (str): The user's full name.
        user_type (str): The type of the user (e.g., 'STUDENT', 'COORDINATOR').
    """

    id: int
    email: str
    full_name: str
    user_type: str

    model_config = {"from_attributes": True}


class NoticeTeamMember(BaseModel):
    """
    Detailed schema for a notice team member, including user information and assignment details.

    Attributes:
        id (int): The unique identifier of the team assignment.
        user_id (int): The ID of the user.
        role (str): The role in the notice team.
        assigned_at (datetime): The timestamp of when the user was assigned.
        user (UserInfo): Detailed information about the assigned user.
    """

    id: int
    user_id: int
    assigned_at: datetime
    user: UserInfo

    model_config = {"from_attributes": True}


class NoticeTeam(NoticeTeamBase):
    """
    Schema representing a team assignment linked to a specific notice.

    Attributes:
        id (int): The unique identifier of the team assignment.
        notice_id (int): The ID of the notice.
        assigned_at (datetime): The timestamp of when the user was assigned.
    """

    id: int
    notice_id: int
    assigned_at: datetime

    model_config = {"from_attributes": True}


class NoticeBase(BaseModel):
    """
    Base schema for notice (edital) data, including titles, dates, and allowance flags.

    Attributes:
        title (str): The title of the notice.
        year (int): The year of validity (2000-3000).
        registration_start_date (datetime): Start date for registrations.
        registration_end_date (Optional[datetime]): End date for registrations.
        appeal_start_date (Optional[datetime]): Start date for the appeal phase.
        appeal_end_date (Optional[datetime]): End date for the appeal phase.
        preliminary_result_date (Optional[datetime]): Date for preliminary result release.
        final_result_date (Optional[datetime]): Date for final result release.
        description (str): Detailed description of the notice.
        food_allowance (bool): Flag for food allowance availability (default False).
        housing_allowance (bool): Flag for housing allowance availability (default False).
        daycare_allowance (bool): Flag for daycare allowance availability (default False).
        graduation_scholarship (bool): Flag for graduation scholarship availability (default False).
    """

    title: str = Field(..., min_length=1, max_length=255)

    registration_start_date: datetime = Field(
        ..., description="Data de início das inscrições"
    )
    registration_end_date: Optional[datetime] = Field(
        None, description="Data de término das inscrições"
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

    description: str = Field(..., min_length=1)

    food_allowance: bool = False
    housing_allowance: bool = False
    daycare_allowance: bool = False
    graduation_scholarship: bool = False


class NoticeCreate(NoticeBase):
    """Schema for creating a new notice. Extends `NoticeBase` without adding new fields."""

    team_members: List[int] = Field(
        default_factory=lambda: cast(List[int], []),
        description="Lista de IDs dos membros da equipe atribuídos ao edital",
    )


class NoticeInfo(NoticeBase):
    """
    Schema for basic information about a notice, including its ID.

    Attributes:
        id (int): The unique identifier of the notice.
    """

    id: int

    model_config = {"from_attributes": True}


class NoticeUpdate(BaseModel):
    """
    Schema for updating a notice, allowing all fields from `NoticeBase` to be optional.

    Attributes:
        title (Optional[str]): New title for the notice.
        year (Optional[int]): New year of validity.
        # ... All other fields from NoticeBase are Optional[type]
    """

    title: Optional[str] = Field(None, min_length=1, max_length=255)

    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None

    appeal_start_date: Optional[datetime] = None
    appeal_end_date: Optional[datetime] = None

    preliminary_result_date: Optional[datetime] = None
    final_result_date: Optional[datetime] = None

    description: Optional[str] = Field(None, min_length=1)

    food_allowance: Optional[bool] = None
    housing_allowance: Optional[bool] = None
    daycare_allowance: Optional[bool] = None
    graduation_scholarship: Optional[bool] = None


class Notice(NoticeBase):
    """
    The main schema for retrieving a full notice object, including relational data.

    Attributes:
        id (int): The unique identifier of the notice.
        created_at (datetime): Timestamp when the notice was created.
        updated_at (datetime): Timestamp when the notice was last updated.
        documents (List[DocumentWithUrl]): List of documents associated with the notice, including URLs.
        team_members (List[NoticeTeamMember]): List of assigned team members.
    """

    id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentWithUrl] = Field(
        default_factory=lambda: cast(List[DocumentWithUrl], [])
    )
    team_members: List[NoticeTeamMember] = Field(
        default_factory=lambda: cast(List[NoticeTeamMember], [])
    )

    model_config = {"from_attributes": True}


class NoticeForStudent(NoticeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentWithUrl] = Field(
        default_factory=lambda: cast(List[DocumentWithUrl], [])
    )
    is_registered: bool = Field(
        default=False, description="Se o estudante já está inscrito neste edital"
    )

    model_config = {"from_attributes": True}
