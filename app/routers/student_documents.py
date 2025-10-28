from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserType
from app.routers.auth import get_current_user
from app.schemas.student_document import (
    StudentDocumentCreate,
    StudentDocumentList,
    StudentDocumentResponse,
    StudentDocumentUpdate,
)
from app.services.student_document_service import StudentDocumentService
from app.services.student_registration_service import StudentRegistrationService

router = APIRouter()


@router.get("/registration/{registration_id}", response_model=StudentDocumentList)
async def get_documents_by_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    registration = await StudentRegistrationService.get_registration_by_id(
        db, registration_id
    )
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada"
        )

    if (
        current_user.user_type not in [UserType.COORDINATOR, UserType.SOCIAL_WORKER]
        and registration.student_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado aos documentos desta inscrição",
        )

    documents = await StudentDocumentService.get_documents_by_registration(
        db, registration_id
    )

    total_count = await StudentDocumentService.count_documents_by_registration(
        db, registration_id
    )

    documents_response = [StudentDocumentResponse.from_model(doc) for doc in documents]

    return StudentDocumentList(documents=documents_response, total=total_count)


@router.post(
    "/registration/{registration_id}/upload", response_model=StudentDocumentResponse
)
async def upload_document(
    registration_id: int,
    file: UploadFile = File(...),
    description: str = Form(None, description="Descrição adicional"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    registration = await StudentRegistrationService.get_registration_by_id(
        db, registration_id
    )
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada"
        )

    if registration.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode fazer upload em suas próprias inscrições",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome do arquivo é obrigatório",
        )

    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não permitido. Tipos aceitos: {', '.join(allowed_types)}",
        )

    max_size = 5 * 1024 * 1024  # 5MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo muito grande. Tamanho máximo: 5MB",
        )

    try:
        document_data = StudentDocumentCreate(
            name=file.filename, description=description
        )

        document = await StudentDocumentService.upload_document(
            db=db,
            registration_id=registration_id,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            document_data=document_data,
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao fazer upload do documento",
            )

        return StudentDocumentResponse.from_model(document)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload do documento: {str(e)}",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await StudentDocumentService.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado"
        )

    if document.student_registration.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode deletar seus próprios documentos",
        )

    success = await StudentDocumentService.delete_document(db, document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar documento",
        )

    return {"message": "Documento deletado com sucesso"}
