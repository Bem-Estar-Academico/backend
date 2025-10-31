from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import OCRStatus, StudentDocument
from app.models.registration import StudentRegistration
from app.models.user import User, UserType
from app.routers.student_documents import (
    delete_document,
    get_documents_by_registration,
    get_ocr_result,
    trigger_ocr_processing,
    upload_document,
)
from app.schemas.student_document import StudentDocumentList, StudentDocumentResponse
from app.services.student_document_service import StudentDocumentService
from app.services.student_registration_service import StudentRegistrationService


@pytest.fixture
def db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def current_user_student():
    return User(
        id=1,
        email="student@example.com",
        full_name="Student User",
        user_type=UserType.STUDENT,
    )


@pytest.fixture
def current_user_coordinator():
    return User(
        id=2,
        email="coordinator@example.com",
        full_name="Coordinator User",
        user_type=UserType.COORDINATOR,
    )


@pytest.fixture
def mock_registration():
    registration = MagicMock(spec=StudentRegistration)
    registration.id = 1
    registration.student_id = 1
    registration.student = MagicMock(
        spec=User, full_name="Student User", cpf="123.456.789-00"
    )
    registration.answer = {"full_name": "Student User", "cpf": "123.456.789-00"}
    return registration


@pytest.fixture
def mock_document():
    document = MagicMock(spec=StudentDocument)
    document.id = 1
    document.student_registration_id = 1
    document.name = "Test Document"
    document.description = "A test document"
    document.file_key = "test_file.pdf"
    document.file_type = "application/pdf"
    document.file_size = 1024
    document.uploaded_at = datetime.now()
    document.file_url = "http://example.com/test_file.pdf"
    document.ocr_status = OCRStatus.PENDING
    document.ocr_results = None
    document.student_registration = MagicMock(spec=StudentRegistration)
    document.student_registration.student_id = 1
    document.student_registration.student = MagicMock(
        spec=User, full_name="Student User", cpf="123.456.789-00"
    )
    document.student_registration.answer = {
        "full_name": "Student User",
        "cpf": "123.456.789-00",
    }
    return document


@pytest.mark.asyncio
async def test_get_documents_by_registration_student_own(
    db_session, current_user_student, mock_registration, mock_document
):
    with patch.object(
        StudentRegistrationService,
        "get_registration_by_id",
        AsyncMock(return_value=mock_registration),
    ) as mock_get_registration:
        with patch.object(
            StudentDocumentService,
            "get_documents_by_registration",
            AsyncMock(return_value=[mock_document]),
        ) as mock_get_docs:
            with patch.object(
                StudentDocumentService,
                "count_documents_by_registration",
                AsyncMock(return_value=1),
            ) as mock_count_docs:
                response = await get_documents_by_registration(
                    1, db_session, current_user_student
                )
                mock_get_registration.assert_called_once_with(db_session, 1)
                mock_get_docs.assert_called_once_with(db_session, 1)
                mock_count_docs.assert_called_once_with(db_session, 1)
                assert isinstance(response, StudentDocumentList)
                assert len(response.documents) == 1
                assert response.total == 1


@pytest.mark.asyncio
async def test_get_documents_by_registration_coordinator(
    db_session, current_user_coordinator, mock_registration, mock_document
):
    with patch.object(
        StudentRegistrationService,
        "get_registration_by_id",
        AsyncMock(return_value=mock_registration),
    ) as mock_get_registration:
        with patch.object(
            StudentDocumentService,
            "get_documents_by_registration",
            AsyncMock(return_value=[mock_document]),
        ) as mock_get_docs:
            with patch.object(
                StudentDocumentService,
                "count_documents_by_registration",
                AsyncMock(return_value=1),
            ) as mock_count_docs:
                response = await get_documents_by_registration(
                    1, db_session, current_user_coordinator
                )
                mock_get_registration.assert_called_once_with(db_session, 1)
                mock_get_docs.assert_called_once_with(db_session, 1)
                mock_count_docs.assert_called_once_with(db_session, 1)
                assert isinstance(response, StudentDocumentList)
                assert len(response.documents) == 1
                assert response.total == 1


@pytest.mark.asyncio
async def test_get_documents_by_registration_forbidden(
    db_session, current_user_student, mock_registration
):
    mock_registration.student_id = 999  # Different student
    with patch.object(
        StudentRegistrationService,
        "get_registration_by_id",
        AsyncMock(return_value=mock_registration),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_documents_by_registration(1, db_session, current_user_student)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_upload_document_success(
    db_session, current_user_student, mock_registration, mock_document
):
    with patch.object(
        StudentRegistrationService,
        "get_registration_by_id",
        AsyncMock(return_value=mock_registration),
    ):
        with patch.object(
            StudentDocumentService,
            "upload_document",
            AsyncMock(return_value=mock_document),
        ) as mock_upload_doc:
            mock_file = MagicMock()
            mock_file.filename = "test.pdf"
            mock_file.content_type = "application/pdf"
            mock_file.read = AsyncMock(return_value=b"file_content")
            response = await upload_document(
                1, mock_file, "description", db_session, current_user_student
            )
            mock_upload_doc.assert_called_once()
            assert isinstance(response, StudentDocumentResponse)


@pytest.mark.asyncio
async def test_delete_document_success(db_session, current_user_student, mock_document):
    with patch.object(
        StudentDocumentService,
        "get_document_by_id",
        AsyncMock(return_value=mock_document),
    ):
        with patch.object(
            StudentDocumentService, "delete_document", AsyncMock(return_value=True)
        ) as mock_delete_doc:
            response = await delete_document(1, db_session, current_user_student)
            mock_delete_doc.assert_called_once_with(db_session, 1)
            assert response == {"message": "Documento deletado com sucesso"}


@pytest.mark.asyncio
async def test_trigger_ocr_processing_success(
    db_session, current_user_coordinator, mock_document
):
    with patch.object(
        StudentDocumentService,
        "get_document_by_id",
        AsyncMock(return_value=mock_document),
    ):
        with patch(
            "app.routers.student_documents.BackgroundTasks"
        ) as MockBackgroundTasks:
            mock_background_tasks_instance = MockBackgroundTasks.return_value
            db_session.add = MagicMock()
            db_session.commit = AsyncMock()
            response = await trigger_ocr_processing(
                1, mock_background_tasks_instance, db_session, current_user_coordinator
            )
            db_session.add.assert_called_once_with(mock_document)
            db_session.commit.assert_called_once()
            mock_background_tasks_instance.add_task.assert_called_once()
            assert response == {
                "message": "Processamento OCR iniciado.",
                "status": "PROCESSING",
            }


@pytest.mark.asyncio
async def test_get_ocr_result_success(
    db_session, current_user_coordinator, mock_document
):
    mock_document.ocr_status = OCRStatus.SUCCESS
    mock_document.ocr_results = {"nome": "STUDENT USER", "cpf": "123.456.789-00"}
    with patch.object(
        StudentDocumentService,
        "get_document_by_id",
        AsyncMock(return_value=mock_document),
    ):
        response = await get_ocr_result(1, db_session, current_user_coordinator)
        assert response["status"] == OCRStatus.SUCCESS.value
        assert response["extracted_data"] == {
            "nome": "STUDENT USER",
            "cpf": "123.456.789-00",
        }
        assert response["comparison"]["document_vs_profile"]["name_match"] is True
        assert response["comparison"]["document_vs_profile"]["cpf_match"] is True
