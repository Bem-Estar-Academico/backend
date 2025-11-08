from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
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
    mocked_db_session.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=total_registrations)),
        MagicMock(scalar_one=MagicMock(return_value=final_status_registrations)),
        MagicMock(mappings=MagicMock(return_value=[{"id": 1, "full_name": "Test User"}]))
    ]

    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)
    expected_progress = (final_status_registrations / total_registrations) * 100
    assert len(team_members) == 1
    assert "progress" in team_members[0]
    assert team_members[0]["progress"] == round(expected_progress)


@pytest.mark.asyncio
async def test_get_team_for_notice_progress_no_registrations(
    mocked_db_session: AsyncMock,
):
    """Test case for progress calculation when there are no registrations."""
    notice_id = 1
    mocked_db_session.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(mappings=MagicMock(return_value=[{"id": 1, "full_name": "Test User"}]))
    ]

    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)
    assert len(team_members) == 1
    assert team_members[0]["progress"] == 0


@pytest.mark.asyncio
async def test_get_team_for_notice_progress_all_final_status(
    mocked_db_session: AsyncMock,
):
    """Test case for progress calculation when all registrations have a final status."""
    notice_id = 1
    total_registrations = 10
    mocked_db_session.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=total_registrations)),
        MagicMock(mappings=MagicMock(return_value=[{"id": 1, "full_name": "Test User"}]))
    ]
    team_members = await NoticeService.get_team_for_notice(mocked_db_session, notice_id)
    assert len(team_members) == 1
    assert team_members[0]["progress"] == 100
