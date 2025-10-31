from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Document, Notice, NoticeTeam
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate, NoticeUpdate
from app.services.notice_service import NoticeService


@pytest.fixture
def mocked_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    return session


@pytest.fixture
def mock_coordinator_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.user_type = UserType.COORDINATOR
    user.full_name = "Test Coordinator"
    user.email = "coordinator@test.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_student_user():
    user = MagicMock(spec=User)
    user.id = 2
    user.user_type = UserType.STUDENT
    user.full_name = "Test Student"
    return user


@pytest.fixture
def mock_notice():
    notice = MagicMock(spec=Notice)
    notice.id = 1
    notice.title = "Test Notice"
    notice.registration_start_date = datetime.now(timezone.utc) - timedelta(days=5)
    notice.registration_end_date = datetime.now(timezone.utc) + timedelta(days=5)
    notice.created_at = datetime.now(timezone.utc)
    notice.documents = []
    notice.team_members = []
    return notice


@pytest.fixture
def mock_notice_create_data():
    now = datetime.now(timezone.utc)
    return NoticeCreate(
        title="New Notice",
        registration_start_date=now,
        registration_end_date=now + timedelta(days=10),
        appeal_start_date=now + timedelta(days=11),
        appeal_end_date=now + timedelta(days=15),
        preliminary_result_date=now + timedelta(days=16),
        final_result_date=now + timedelta(days=20),
        description="A new notice for testing",
        food_allowance=True,
        housing_allowance=False,
        daycare_allowance=True,
        graduation_scholarship=False,
    )


@pytest.fixture
def mock_notice_update_data():
    return NoticeUpdate(
        title="Updated Notice Title",
        description="Updated description for the notice",
    )


@pytest.fixture
def mock_document():
    document = MagicMock(spec=Document)
    document.id = 1
    document.notice_id = 1
    document.name = "test_document.pdf"
    document.file_key = "test/test_document.pdf"
    document.file_type = "application/pdf"
    document.file_size = 1024
    document.uploaded_at = datetime.now(timezone.utc)
    return document


@pytest.mark.asyncio
async def test_get_notice_by_id_success(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
) -> None:
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    notice = await NoticeService.get_notice_by_id(mocked_db_session, 1)
    assert notice == mock_notice


@pytest.mark.asyncio
async def test_get_notice_by_id_not_found(mocked_db_session: AsyncMock) -> None:
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    notice = await NoticeService.get_notice_by_id(mocked_db_session, 999)
    assert notice is None


@pytest.mark.asyncio
async def test_get_notices_no_filter(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_notice
    ]
    notices = await NoticeService.get_notices(mocked_db_session)
    assert len(notices) == 1
    assert notices[0] == mock_notice


@pytest.mark.asyncio
async def test_get_notices_with_year_filter(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_notice
    ]
    notices = await NoticeService.get_notices(
        mocked_db_session, year=mock_notice.created_at.year
    )
    assert len(notices) == 1
    assert notices[0] == mock_notice


@pytest.mark.asyncio
async def test_get_notices_no_results(mocked_db_session: AsyncMock):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = []
    notices = await NoticeService.get_notices(mocked_db_session)
    assert len(notices) == 0


@pytest.mark.asyncio
async def test_create_notice_success(
    mocked_db_session: AsyncMock,
    mock_notice_create_data: MagicMock,
    mock_coordinator_user: MagicMock,
):
    created_notice = Notice(
        **mock_notice_create_data.model_dump(exclude={"team_members"}), id=1
    )
    with patch(
        "app.services.notice_service.NoticeService.get_notice_by_id",
        AsyncMock(return_value=created_notice),
    ):
        notice = await NoticeService.create_notice(
            mocked_db_session, mock_notice_create_data, mock_coordinator_user.id
        )
        mocked_db_session.add.assert_called()
        mocked_db_session.flush.assert_called_once()
        mocked_db_session.commit.assert_called_once()
        mocked_db_session.refresh.assert_called_once()
        assert notice.title == mock_notice_create_data.title


@pytest.mark.asyncio
async def test_create_notice_with_team_members(
    mocked_db_session: AsyncMock,
    mock_notice_create_data: MagicMock,
    mock_coordinator_user: MagicMock,
):
    mock_notice_create_data.team_members = [
        mock_coordinator_user.id,
        99,
    ]  # Add another user
    created_notice = Notice(
        **mock_notice_create_data.model_dump(exclude={"team_members"}), id=1
    )
    with patch(
        "app.services.notice_service.NoticeService.get_notice_by_id",
        AsyncMock(return_value=created_notice),
    ):
        notice = await NoticeService.create_notice(
            mocked_db_session, mock_notice_create_data, mock_coordinator_user.id
        )
        assert (
            mocked_db_session.add.call_count == 3
        )  # Notice, creator, and additional member
        mocked_db_session.flush.assert_called_once()
        mocked_db_session.commit.assert_called_once()
        mocked_db_session.refresh.assert_called_once()
        assert notice.title == mock_notice_create_data.title


# Test update_notice
@pytest.mark.asyncio
async def test_update_notice_success(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_notice_update_data: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    updated_notice = await NoticeService.update_notice(
        mocked_db_session, mock_notice.id, mock_notice_update_data
    )
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(mock_notice)
    assert updated_notice is not None
    assert updated_notice.title == mock_notice_update_data.title
    assert updated_notice.description == mock_notice_update_data.description


@pytest.mark.asyncio
async def test_update_notice_not_found(
    mocked_db_session: AsyncMock, mock_notice_update_data: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    updated_notice = await NoticeService.update_notice(
        mocked_db_session, 999, mock_notice_update_data
    )
    assert updated_notice is None
    mocked_db_session.commit.assert_not_called()
    mocked_db_session.refresh.assert_not_called()


@pytest.mark.asyncio
async def test_delete_notice_success(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    result = await NoticeService.delete_notice(mocked_db_session, mock_notice.id)
    assert result is True
    mocked_db_session.delete.assert_called_once_with(mock_notice)
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_notice_not_found(mocked_db_session: AsyncMock):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    result = await NoticeService.delete_notice(mocked_db_session, 999)
    assert result is False
    mocked_db_session.delete.assert_not_called()
    mocked_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_active_notices(mocked_db_session: AsyncMock, mock_notice: MagicMock):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_notice
    ]
    active_notices = await NoticeService.get_active_notices(mocked_db_session)
    assert len(active_notices) == 1
    assert active_notices[0] == mock_notice


# Test get_notices_for_student
@pytest.mark.asyncio
async def test_get_notices_for_student_registered(
    mocked_db_session: AsyncMock, mock_notice: MagicMock, mock_student_user: MagicMock
):
    mock_row = MagicMock()
    mock_row.Notice = mock_notice
    mock_row.is_registered = True
    mocked_db_session.execute.return_value = [mock_row]
    notices_data = await NoticeService.get_notices_for_student(
        mocked_db_session, mock_student_user.id
    )
    assert len(notices_data) == 1
    assert notices_data[0]["id"] == mock_notice.id
    assert notices_data[0]["is_registered"] is True


@pytest.mark.asyncio
async def test_get_notices_for_student_not_registered(
    mocked_db_session: AsyncMock, mock_notice: MagicMock, mock_student_user: MagicMock
):
    mock_row = MagicMock()
    mock_row.Notice = mock_notice
    mock_row.is_registered = False
    mocked_db_session.execute.return_value = [mock_row]
    notices_data = await NoticeService.get_notices_for_student(
        mocked_db_session, mock_student_user.id
    )
    assert len(notices_data) == 1
    assert notices_data[0]["id"] == mock_notice.id
    assert notices_data[0]["is_registered"] is False


@pytest.mark.asyncio
async def test_get_notices_by_year(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_notice
    ]
    notices = await NoticeService.get_notices_by_year(
        mocked_db_session, mock_notice.created_at.year
    )
    assert len(notices) == 1
    assert notices[0] == mock_notice


@pytest.mark.asyncio
async def test_add_team_member_to_notice_success(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_coordinator_user: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        mock_notice,
        None,
        MagicMock(spec=NoticeTeam),
    ]
    mocked_db_session.execute.return_value.scalar_one.return_value = MagicMock(
        spec=NoticeTeam
    )  # For the refresh
    team_member = await NoticeService.add_team_member_to_notice(
        mocked_db_session, mock_notice.id, mock_coordinator_user.id
    )
    assert team_member is not None
    mocked_db_session.add.assert_called_once()
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_add_team_member_to_notice_already_exists(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_coordinator_user: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        mock_notice,
        MagicMock(spec=NoticeTeam),
    ]
    team_member = await NoticeService.add_team_member_to_notice(
        mocked_db_session, mock_notice.id, mock_coordinator_user.id
    )
    assert team_member is None
    mocked_db_session.add.assert_not_called()
    mocked_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_team_member_to_notice_notice_not_found(
    mocked_db_session: AsyncMock, mock_coordinator_user: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    team_member = await NoticeService.add_team_member_to_notice(
        mocked_db_session, 999, mock_coordinator_user.id
    )
    assert team_member is None
    mocked_db_session.add.assert_not_called()
    mocked_db_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_upload_document_to_notice_success(
    mock_storage_instance: MagicMock,
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
):
    mock_storage_instance.upload_file.return_value = "new_file_key"
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    document = await NoticeService.upload_document_to_notice(
        mocked_db_session, mock_notice.id, b"file_content", "filename.txt", "text/plain"
    )
    mock_storage_instance.upload_file.assert_called_once()
    mocked_db_session.add.assert_called_once()
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once()
    assert document is not None
    assert document.file_key == "new_file_key"


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_upload_document_to_notice_notice_not_found(
    mock_storage_instance: MagicMock, mocked_db_session: AsyncMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    document = await NoticeService.upload_document_to_notice(
        mocked_db_session, 999, b"file_content", "filename.txt", "text/plain"
    )
    assert document is None
    mock_storage_instance.upload_file.assert_not_called()
    mocked_db_session.add.assert_not_called()
    mocked_db_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_upload_document_to_notice_upload_error(
    mock_storage_instance: MagicMock,
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
):
    mock_storage_instance.upload_file.side_effect = Exception("Upload failed")
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    with pytest.raises(Exception, match="Error uploading document: Upload failed"):
        await NoticeService.upload_document_to_notice(
            mocked_db_session,
            mock_notice.id,
            b"file_content",
            "filename.txt",
            "text/plain",
        )
    mocked_db_session.rollback.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_delete_document_success(
    mock_storage_instance: MagicMock,
    mocked_db_session: AsyncMock,
    mock_document: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_document
    )
    result = await NoticeService.delete_document(mocked_db_session, mock_document.id)
    assert result is True
    mock_storage_instance.delete_file.assert_called_once_with(mock_document.file_key)
    mocked_db_session.delete.assert_called_once_with(mock_document)
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_delete_document_not_found(
    mock_storage_instance: MagicMock, mocked_db_session: AsyncMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    result = await NoticeService.delete_document(mocked_db_session, 999)
    assert result is False
    mock_storage_instance.delete_file.assert_not_called()
    mocked_db_session.delete.assert_not_called()
    mocked_db_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_get_document_download_url_success(
    mock_storage_instance: MagicMock,
    mocked_db_session: AsyncMock,
    mock_document: MagicMock,
):
    mock_storage_instance.generate_signed_url.return_value = (
        "http://mock-s3-url/some_file_key"
    )
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_document
    )
    url = await NoticeService.get_document_download_url(
        mocked_db_session, mock_document.id
    )
    assert url == "http://mock-s3-url/some_file_key"
    mock_storage_instance.generate_signed_url.assert_called_once_with(
        mock_document.file_key, 3600
    )


@pytest.mark.asyncio
@patch("app.core.storage_factory.StorageFactory._instance")
async def test_get_document_download_url_not_found(
    mock_storage_instance: MagicMock, mocked_db_session: AsyncMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    url = await NoticeService.get_document_download_url(mocked_db_session, 999)
    assert url is None
    mock_storage_instance.generate_signed_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_team_for_notice(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_coordinator_user: MagicMock,
):
    mock_row: Dict[str, Any] = {
        "id": mock_coordinator_user.id,
        "email": mock_coordinator_user.email,
        "full_name": mock_coordinator_user.full_name,
        "is_active": mock_coordinator_user.is_active,
        "user_type": mock_coordinator_user.user_type,
        "last_review": datetime.now(timezone.utc),
    }

    mocked_db_session.execute.return_value.mappings.return_value = [mock_row]
    team_members = await NoticeService.get_team_for_notice(
        mocked_db_session, mock_notice.id
    )
    assert len(team_members) == 1
    assert team_members[0]["id"] == mock_coordinator_user.id
    assert "progress" in team_members[0]
