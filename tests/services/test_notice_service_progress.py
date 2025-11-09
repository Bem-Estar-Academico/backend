from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserType
from app.services.notice_service import NoticeService


@pytest.fixture
def mocked_db_session():
    """Fixture to create a mocked async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_team_for_notice_progress_calculation(
    mocked_db_session: AsyncMock,
):
    """Test case to verify the progress calculation in get_team_for_notice."""
    notice_id = 1
    total_registrations = 10
    final_status_registrations = 5

    total_registrations_mock = MagicMock()
    total_registrations_mock.scalar_one.return_value = total_registrations

    final_status_mock = MagicMock()
    final_status_mock.scalar_one.return_value = final_status_registrations

    team_member_data = {
        "id": 1,
        "full_name": "Test User",
        "email": "test@test.com",
        "is_active": True,
        "user_type": UserType.SOCIAL_WORKER,
        "last_review": None,
    }

    team_members_mock = MagicMock()
    team_members_mock.mappings.return_value = [team_member_data]

    progress_mock = MagicMock()
    progress_data_mock = MagicMock()
    progress_data_mock.total_reviews = 10
    progress_data_mock.completed_reviews = 5
    progress_mock.first.return_value = progress_data_mock

    mocked_db_session.execute.side_effect = [
        total_registrations_mock,
        final_status_mock,
        team_members_mock,
        progress_mock,
    ]

    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)

    assert len(team_members) == 1
    assert "progress" in team_members[0]
    assert team_members[0]["progress"] == 50.0  # (5/10) * 100


@pytest.mark.asyncio
async def test_get_team_for_notice_progress_no_registrations(
    mocked_db_session: AsyncMock,
):
    """Test case for progress calculation when there are no registrations."""
    notice_id = 1

    total_registrations_mock = MagicMock()
    total_registrations_mock.scalar_one.return_value = 0

    team_member_data = {
        "id": 1,
        "full_name": "Test User",
        "email": "test@test.com",
        "is_active": True,
        "user_type": UserType.COORDINATOR,
        "last_review": None,
    }

    team_members_mock = MagicMock()
    team_members_mock.mappings.return_value = [team_member_data]

    # When total_registrations is 0, only 2 queries are executed (no final status query)
    mocked_db_session.execute.side_effect = [
        total_registrations_mock,  # Total registrations query
        team_members_mock,  # Team members query
    ]

    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)
    assert len(team_members) == 1
    assert team_members[0]["progress"] == 100.0  # Coordinator always gets 100%


@pytest.mark.asyncio
async def test_get_team_for_notice_progress_all_final_status(
    mocked_db_session: AsyncMock,
):
    """Test case for progress calculation when all registrations have a final status."""
    notice_id = 1
    total_registrations = 10

    total_registrations_mock = MagicMock()
    total_registrations_mock.scalar_one.return_value = total_registrations

    final_status_mock = MagicMock()
    final_status_mock.scalar_one.return_value = total_registrations

    team_member_data = {
        "id": 1,
        "full_name": "Test User",
        "email": "test@test.com",
        "is_active": True,
        "user_type": UserType.SOCIAL_WORKER,
        "last_review": None,
    }

    team_members_mock = MagicMock()
    team_members_mock.mappings.return_value = [team_member_data]

    progress_mock = MagicMock()
    progress_data_mock = MagicMock()
    progress_data_mock.total_reviews = 10
    progress_data_mock.completed_reviews = 10
    progress_mock.first.return_value = progress_data_mock

    mocked_db_session.execute.side_effect = [
        total_registrations_mock,
        final_status_mock,
        team_members_mock,
        progress_mock,
    ]

    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)
    assert len(team_members) == 1
    assert team_members[0]["progress"] == 100.0
