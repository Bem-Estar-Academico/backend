import io
from typing import List, Optional

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage_factory import get_storage_manager
from app.models.notice import OCRStatus, StudentDocument, StudentRegistration
from app.models.registration import StudentRegistration
from app.ocr_processing.improved_ocr import ocr
from app.schemas.student_document import StudentDocumentCreate


class StudentDocumentService:
    """Service para gerenciar documentos dos estudantes"""

    @staticmethod
    async def get_document_by_id(
        db: AsyncSession, document_id: int
    ) -> Optional[StudentDocument]:
        result = await db.execute(
            select(StudentDocument)
            .options(
                selectinload(StudentDocument.student_registration).selectinload(
                    StudentRegistration.student
                )
            )
            .where(StudentDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def process_document_ocr_background(db: AsyncSession, document_id: int):
        """
        Processes a student document with OCR in the background,
        updates its status, and saves the results.
        """
        document = None
        try:
            doc_result = await db.execute(
                select(StudentDocument).where(StudentDocument.id == document_id)
            )
            document = doc_result.scalar_one_or_none()

            if not document:
                logging.warning(f"Document with ID {document_id} not found.")
                return

            storage = get_storage_manager()
            file_content = storage.download_file_content(document.file_key) # type: ignore
            image = Image.open(io.BytesIO(file_content)) # type: ignore
            ocr_result = ocr(image)

            if "error" in ocr_result:
                document.ocr_status = OCRStatus.FAILED
                document.ocr_results = ocr_result
            else:
                document.ocr_status = OCRStatus.SUCCESS
                document.ocr_results = ocr_result.get("extracted_fields") # type: ignore

            await db.commit()

        except Exception as e:
            print(
                f"An error occurred during OCR processing for document {document_id}: {e}"
            )
            if document:
                await db.rollback()
                document.ocr_status = OCRStatus.FAILED
                document.ocr_results = {"error": str(e)}
                await db.commit()


    @staticmethod
    async def get_documents_by_registration(
        db: AsyncSession, registration_id: int
    ) -> List[StudentDocument]:
        query = select(StudentDocument).where(
            StudentDocument.student_registration_id == registration_id
        )

        result = await db.execute(query.order_by(StudentDocument.uploaded_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def upload_document(
        db: AsyncSession,
        registration_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
        document_data: StudentDocumentCreate,
    ) -> Optional[StudentDocument]:
        """Faz upload de um documento para uma inscrição"""
        storage_manager = get_storage_manager()

        result = await db.execute(
            select(StudentRegistration).where(StudentRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            return None

        try:
            file_key = storage_manager.upload_file(file_content, filename, content_type)

            db_document = StudentDocument(
                student_registration_id=registration_id,
                name=document_data.name or filename,
                file_key=file_key,
                file_type=content_type,
                file_size=len(file_content),
                description=document_data.description,
            )

            db.add(db_document)
            await db.commit()
            await db.refresh(db_document)

            return db_document

        except Exception as e:
            await db.rollback()
            # Re-raise the exception to be handled by the caller
            raise Exception(f"Erro ao fazer upload do documento: {str(e)}")


    @staticmethod
    async def delete_document(db: AsyncSession, document_id: int) -> bool:
        storage_manager = get_storage_manager()

        document = await StudentDocumentService.get_document_by_id(db, document_id)
        if not document:
            return False

        try:
            storage_manager.delete_file(document.file_key)

            await db.delete(document)
            await db.commit()

            return True

        except Exception as e:
            await db.rollback()
            raise Exception(f"Erro ao deletar documento: {str(e)}")

    @staticmethod
    async def get_document_download_url(
        db: AsyncSession, document_id: int, expiration: int = 3600
    ) -> Optional[str]:
        storage_manager = get_storage_manager()

        document = await StudentDocumentService.get_document_by_id(db, document_id)
        if not document:
            return None

        return storage_manager.generate_signed_url(document.file_key, expiration)

    @staticmethod
    async def count_documents_by_registration(
        db: AsyncSession, registration_id: int
    ) -> int:
        result = await db.execute(
            select(func.count(StudentDocument.id)).where(
                StudentDocument.student_registration_id == registration_id
            )
        )
        return result.scalar() or 0
