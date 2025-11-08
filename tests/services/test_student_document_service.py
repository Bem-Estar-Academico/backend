from typing import Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import OCRStatus, StudentDocument
from app.models.registration import StudentRegistration
from app.schemas.student_document import StudentDocumentCreate
from app.services.student_document_service import StudentDocumentService


@pytest.fixture
def mocked_db_session() -> AsyncMock:
    session: AsyncMock = AsyncMock(spec=AsyncSession)
    execute_mock: MagicMock = MagicMock()
    session.execute.return_value = execute_mock
    execute_mock.scalar_one_or_none.return_value = MagicMock()
    scalars_mock: MagicMock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    scalars_mock.all.return_value = MagicMock()
    execute_mock.scalar.return_value = MagicMock()
    return session


@pytest.fixture
def mock_storage_manager() -> MagicMock:
    mock_manager: MagicMock = MagicMock()
    mock_manager.upload_file.return_value = "test_file_key"
    mock_manager.download_file_content.return_value = b"fake_file_content"
    mock_manager.delete_file.return_value = True
    mock_manager.generate_signed_url.return_value = "http://signed.url"
    return mock_manager


@pytest.fixture(autouse=True)
def mock_get_storage_manager(mock_storage_manager: MagicMock) -> Generator[None, None, None]:
    with patch(
        "app.services.student_document_service.get_storage_manager",
        return_value=mock_storage_manager,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_ocr() -> Generator[MagicMock, None, None]:
    with patch("app.services.student_document_service.ocr") as mock_ocr_func:
        mock_ocr_func.return_value = {
            "extracted_fields": {"nome": "TEST", "cpf": "123.456.789-00"}
        }
        yield mock_ocr_func


@pytest.fixture(autouse=True)
def mock_image_open() -> Generator[MagicMock, None, None]:
    with patch("PIL.Image.open") as mock_open:
        yield mock_open


@pytest.mark.asyncio
async def test_get_document_by_id(mocked_db_session: AsyncMock) -> None:
    mock_document: MagicMock = MagicMock(spec=StudentDocument)
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_document
    document = await StudentDocumentService.get_document_by_id(mocked_db_session, 1)
    assert document == mock_document
    mocked_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_process_document_ocr_background_success(
    mocked_db_session: AsyncMock, mock_ocr: MagicMock
) -> None:
    mock_document: MagicMock = MagicMock(spec=StudentDocument)
    mock_document.id = 1
    mock_document.ocr_status = OCRStatus.PENDING
    mock_document.file_key = "test_file_key"
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_document

    await StudentDocumentService.process_document_ocr_background(mocked_db_session, 1)

    assert mock_document.ocr_status == OCRStatus.SUCCESS
    assert mock_document.ocr_results == {"nome": "TEST", "cpf": "123.456.789-00"}
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_document_ocr_background_failed(
    mocked_db_session: AsyncMock, mock_ocr: MagicMock
) -> None:
    mock_document: MagicMock = MagicMock(spec=StudentDocument)
    mock_document.id = 1
    mock_document.ocr_status = OCRStatus.PENDING
    mock_document.file_key = "test_file_key"
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_document
    mock_ocr.return_value = {"error": "OCR Error"}

    await StudentDocumentService.process_document_ocr_background(mocked_db_session, 1)

    assert mock_document.ocr_status == OCRStatus.FAILED
    assert mock_document.ocr_results == {"error": "OCR Error"}
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_documents_by_registration(mocked_db_session: AsyncMock) -> None:
    mock_documents: List[MagicMock] = [MagicMock(spec=StudentDocument)]
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = mock_documents
    documents = await StudentDocumentService.get_documents_by_registration(
        mocked_db_session, 1
    )
    assert documents == mock_documents
    mocked_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_success(
    mocked_db_session: AsyncMock, mock_storage_manager: MagicMock
) -> None:
    mock_registration: MagicMock = MagicMock(spec=StudentRegistration)
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_registration
    mocked_db_session.add = MagicMock()
    mocked_db_session.commit = AsyncMock()
    mocked_db_session.refresh = AsyncMock()

    document_data: StudentDocumentCreate = StudentDocumentCreate(name="test_doc", description="desc")
    file_content: bytes = b"file_content"
    filename: str = "test.pdf"
    content_type: str = "application/pdf"

    document = await StudentDocumentService.upload_document(
        mocked_db_session, 1, file_content, filename, content_type, document_data
    )

    # document may be a model instance; ensure it's not None before accessing attrs
    assert document is not None
    mock_storage_manager.upload_file.assert_called_once_with(
        file_content, filename, content_type
    )
    mocked_db_session.add.assert_called_once()
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(document)
    # Access attribute after asserting not None
    assert getattr(document, "file_key", None) == "test_file_key"


@pytest.mark.asyncio
async def test_delete_document_success(
    mocked_db_session: AsyncMock, mock_storage_manager: MagicMock
) -> None:
    mock_document: MagicMock = MagicMock(spec=StudentDocument)
    mock_document.file_key = "test_file_key"
    with patch.object(
        StudentDocumentService,
        "get_document_by_id",
        new=AsyncMock(return_value=mock_document),
    ) as mock_get_doc:
        mocked_db_session.delete = AsyncMock()
        mocked_db_session.commit = AsyncMock()

        result = await StudentDocumentService.delete_document(mocked_db_session, 1)

        mock_get_doc.assert_called_once_with(mocked_db_session, 1)
        mock_storage_manager.delete_file.assert_called_once_with("test_file_key")
        mocked_db_session.delete.assert_called_once_with(mock_document)
        mocked_db_session.commit.assert_called_once()
        assert result is True


@pytest.mark.asyncio
async def test_get_document_download_url(
    mocked_db_session: AsyncMock, mock_storage_manager: MagicMock
) -> None:
    mock_document: MagicMock = MagicMock(spec=StudentDocument)
    mock_document.file_key = "test_file_key"
    with patch.object(
        StudentDocumentService,
        "get_document_by_id",
        new=AsyncMock(return_value=mock_document),
    ) as mock_get_doc:
        url = await StudentDocumentService.get_document_download_url(
            mocked_db_session, 1
        )

        mock_get_doc.assert_called_once_with(mocked_db_session, 1)
        mock_storage_manager.generate_signed_url.assert_called_once_with(
            "test_file_key", 3600
        )
        assert url == "http://signed.url"


@pytest.mark.asyncio
async def test_count_documents_by_registration(mocked_db_session: AsyncMock) -> None:
    mocked_db_session.execute.return_value.scalar.return_value = 5
    count = await StudentDocumentService.count_documents_by_registration(
        mocked_db_session, 1
    )
    assert count == 5
    mocked_db_session.execute.assert_called_once()
