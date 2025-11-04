from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.models.notice import StudentDocument


class StudentDocumentBase(BaseModel):
    """Schema base para documentos dos estudantes"""

    name: str = Field(..., description="Nome do arquivo")
    description: Optional[str] = Field(None, description="Descrição adicional")


class StudentDocumentCreate(StudentDocumentBase):
    """Schema para criação de documento do estudante"""

    pass


class StudentDocumentUpdate(BaseModel):
    """Schema para atualização de documento do estudante"""

    name: Optional[str] = None
    description: Optional[str] = None


class StudentDocumentResponse(StudentDocumentBase):
    """Schema para resposta de documento do estudante"""

    id: int
    student_registration_id: int
    file_key: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: datetime
    file_url: str

    @classmethod
    def from_model(
        cls, student_document: "StudentDocument"
    ) -> "StudentDocumentResponse":
        return cls(
            id=student_document.id,
            student_registration_id=student_document.student_registration_id,
            name=student_document.name,
            file_key=student_document.file_key,
            file_type=student_document.file_type,
            file_size=student_document.file_size,
            uploaded_at=student_document.uploaded_at,
            description=student_document.description,
            file_url=student_document.file_url,
        )

    class Config:
        from_attributes = True


class StudentDocumentList(BaseModel):
    """Schema para listagem de documentos"""

    documents: list[StudentDocumentResponse]
    total: int
