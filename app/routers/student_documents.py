from typing import Any, Dict
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_staff
from app.db.database import get_db
from app.models.notice import OCRStatus
from app.models.user import User, UserType
from app.routers.auth import get_current_user
from app.schemas.student_document import (
    StudentDocumentCreate,
    StudentDocumentList,
    StudentDocumentResponse,
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


@router.post("/{document_id}/trigger-ocr", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ocr_processing(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Triggers the OCR processing for a specific document.
    This is intended to be called on-demand by a social worker.
    """
    doc = await StudentDocumentService.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if doc.ocr_status in [OCRStatus.SUCCESS, OCRStatus.PROCESSING]:
        return {
            "message": "Documento já processado ou em processamento.",
            "status": doc.ocr_status.value,
        }
    doc.ocr_status = OCRStatus.PROCESSING
    db.add(doc)
    await db.commit()

    # Schedule the OCR task to run in the background
    background_tasks.add_task(
        StudentDocumentService.process_document_ocr_background, db, document_id
    )

    return {"message": "Processamento OCR iniciado.", "status": "PROCESSING"}


@router.get("/{document_id}/ocr-result")
async def get_ocr_result(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Fetches the result of the OCR processing for a document,
    including a comparison with profile and form data.
    """
    doc = await StudentDocumentService.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    response: Dict[str, Any] = {
        "status": doc.ocr_status.value,
        "extracted_data": doc.ocr_results,
        "comparison": None,
    }
    if doc.ocr_status == OCRStatus.SUCCESS and doc.ocr_results:
        student = doc.student_registration.student
        registration_answers = doc.student_registration.answer or {}

        response["comparison"] = {
            "document_vs_profile": {
                "name_match": student.full_name.upper() == doc.ocr_results.get("nome"),
                "cpf_match": student.cpf == doc.ocr_results.get("cpf"),
            },
            "profile_data": {
                "full_name": student.full_name,
                "cpf": student.cpf,
            },
            "form_data": {
                "full_name": registration_answers.get("full_name"),
                "cpf": registration_answers.get("cpf"),
            },
        }
    return response
