import asyncio
import io
from PIL import Image
from celery import shared_task # type: ignore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.notice import OCRStatus, StudentDocument
from app.core.storage_factory import get_storage_manager
from app.ocr_processing.improved_ocr import ocr


@shared_task # type: ignore
def process_document_ocr(document_id: int):
    """
    Celery task to process a student document with OCR,
    update its status, and save the results.
    """

    async def _run_async():
        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        db: AsyncSession = SessionLocal()

        document = None
        try:
            doc_result = await db.execute(
                select(StudentDocument).where(StudentDocument.id == document_id)
            )
            document = doc_result.scalar_one_or_none()

            if not document:
                print(f"Document with ID {document_id} not found.")
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
            print(f"An error occurred during OCR processing for document {document_id}: {e}")
            if document:
                await db.rollback()
                document.ocr_status = OCRStatus.FAILED
                document.ocr_results = {"error": str(e)}
                await db.commit()
        finally:
            await db.close()
            await engine.dispose()
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run_async())
    finally:
        loop.close()
