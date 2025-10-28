from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage_factory import get_storage_manager
from app.models.notice import StudentDocument, StudentRegistration
from app.models.registration import StudentRegistration
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
