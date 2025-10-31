from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Notice
from app.models.registration import StudentRegistration
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User, UserType
from app.schemas.student_registration import (
    StudentRegistrationBase,
    StudentRegistrationUpdate,
)
from app.services.student_registration_service import StudentRegistrationService


@pytest.fixture
def mocked_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    return session


@pytest.fixture
def mock_student_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.user_type = UserType.STUDENT
    user.full_name = "Test Student"
    user.cpf = "12345678900"
    user.registration_number = "REG123"
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_social_worker_user():
    user = MagicMock(spec=User)
    user.id = 2
    user.user_type = UserType.SOCIAL_WORKER
    user.is_staff = True
    user.full_name = "Test Social Worker"
    return user


@pytest.fixture
def mock_coordinator_user():
    user = MagicMock(spec=User)
    user.id = 3
    user.user_type = UserType.COORDINATOR
    user.is_staff = True
    user.full_name = "Test Coordinator"
    return user


@pytest.fixture
def mock_notice():
    notice = MagicMock(spec=Notice)
    notice.id = 1
    notice.registration_start_date = datetime.now(timezone.utc) - timedelta(days=1)
    notice.registration_end_date = datetime.now(timezone.utc) + timedelta(days=1)
    notice.title = "Test Notice"
    return notice


@pytest.fixture
def mock_student_registration(mock_student_user: MagicMock, mock_notice: MagicMock):
    registration = MagicMock(spec=StudentRegistration)
    registration.id = 1
    registration.student_id = mock_student_user.id
    registration.notice_id = mock_notice.id
    registration.student = mock_student_user
    registration.notice = mock_notice
    registration.answer = {"question": "answer"}
    registration.created_at = datetime.now(timezone.utc)
    registration.review = None
    return registration


@pytest.fixture
def mock_review(mock_social_worker_user: MagicMock):
    review = MagicMock(spec=ReviewRegistrationModel)
    review.id = 1
    review.status = RegistrationStatus.APPROVED
    review.social_worker_id = mock_social_worker_user.id
    review.social_worker = mock_social_worker_user
    review.ivs = 50.0
    return review


@pytest.mark.asyncio
async def test_create_registration_success(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        mock_notice,
        None,
    ]
    registration_data = StudentRegistrationBase(answer={"q1": "a1"})
    registration = await StudentRegistrationService.create_registration(
        mock_notice.id, mocked_db_session, registration_data, mock_student_user
    )
    assert registration.student_id == mock_student_user.id
    assert registration.notice_id == mock_notice.id
    assert registration.answer == {"q1": "a1"}
    mocked_db_session.add.assert_called_once()
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(registration)


@pytest.mark.asyncio
async def test_create_registration_not_student(
    mocked_db_session: AsyncMock,
    mock_social_worker_user: MagicMock,
    mock_notice: MagicMock,
):
    with pytest.raises(HTTPException) as exc_info:
        registration_data = StudentRegistrationBase(answer={"q1": "a1"})
        await StudentRegistrationService.create_registration(
            mock_notice.id,
            mocked_db_session,
            registration_data,
            mock_social_worker_user,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_registration_notice_not_found(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        registration_data = StudentRegistrationBase(answer={"q1": "a1"})
        await StudentRegistrationService.create_registration(
            999, mocked_db_session, registration_data, mock_student_user
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_registration_period_not_active_before_start(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock, mock_notice: MagicMock
):
    mock_notice.registration_start_date = datetime.now(timezone.utc) + timedelta(days=1)
    mock_notice.registration_end_date = datetime.now(timezone.utc) + timedelta(days=2)
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    with pytest.raises(HTTPException) as exc_info:
        registration_data = StudentRegistrationBase(answer={"q1": "a1"})
        await StudentRegistrationService.create_registration(
            mock_notice.id, mocked_db_session, registration_data, mock_student_user
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_registration_period_not_active_after_end(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock, mock_notice: MagicMock
):
    mock_notice.registration_start_date = datetime.now(timezone.utc) - timedelta(days=2)
    mock_notice.registration_end_date = datetime.now(timezone.utc) - timedelta(days=1)
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_notice
    with pytest.raises(HTTPException) as exc_info:
        registration_data = StudentRegistrationBase(answer={"q1": "a1"})
        await StudentRegistrationService.create_registration(
            mock_notice.id, mocked_db_session, registration_data, mock_student_user
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_registration_already_exists(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        mock_notice,
        mock_student_registration,
    ]
    with pytest.raises(HTTPException) as exc_info:
        registration_data = StudentRegistrationBase(answer={"q1": "a1"})
        await StudentRegistrationService.create_registration(
            mock_notice.id, mocked_db_session, registration_data, mock_student_user
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_registration_by_id_success(
    mocked_db_session: AsyncMock, mock_student_registration: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    registration = await StudentRegistrationService.get_registration_by_id(
        mocked_db_session, 1
    )
    assert registration == mock_student_registration


@pytest.mark.asyncio
async def test_get_registration_by_id_not_found(mocked_db_session: AsyncMock):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    registration = await StudentRegistrationService.get_registration_by_id(
        mocked_db_session, 999
    )
    assert registration is None


@pytest.mark.asyncio
async def test_get_registrations_by_student_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]
    mocked_db_session.execute.return_value.scalar_one.return_value = (
        1  # For count_query
    )
    (
        registrations,
        total,
    ) = await StudentRegistrationService.get_registrations_by_student(
        mocked_db_session, mock_student_user.id
    )
    assert len(registrations) == 1
    assert total == 1
    assert registrations[0] == mock_student_registration


@pytest.mark.asyncio
async def test_get_registrations_by_student_no_registrations(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = []
    mocked_db_session.execute.return_value.scalar_one.return_value = (
        0  # For count_query
    )
    (
        registrations,
        total,
    ) = await StudentRegistrationService.get_registrations_by_student(
        mocked_db_session, mock_student_user.id
    )
    assert len(registrations) == 0
    assert total == 0


@pytest.mark.asyncio
async def test_update_registration_student_cancel_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mock_student_registration.review = None  # Ensure no review initially
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(status=RegistrationStatus.CANCELLED)  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session, mock_student_registration.id, update_data, mock_student_user
    )
    assert updated_registration.review.status == RegistrationStatus.CANCELLED  # type: ignore
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_student_cancel_existing_review_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
):
    mock_student_registration.review = mock_review  # Existing review
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(status=RegistrationStatus.CANCELLED)  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session, mock_student_registration.id, update_data, mock_student_user
    )
    assert updated_registration.review.status == RegistrationStatus.CANCELLED  # type: ignore
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_student_update_answer_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(answer={"new_q": "new_a"})  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session, mock_student_registration.id, update_data, mock_student_user
    )
    assert updated_registration.answer == {"new_q": "new_a"}
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_student_not_owner(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mock_student_registration.student_id = 999  # Not the owner
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    with pytest.raises(HTTPException) as exc_info:
        update_data = StudentRegistrationUpdate(status=RegistrationStatus.CANCELLED)  # type: ignore
        await StudentRegistrationService.update_registration(
            mocked_db_session,
            mock_student_registration.id,
            update_data,
            mock_student_user,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_registration_student_invalid_status_update(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    with pytest.raises(HTTPException) as exc_info:
        update_data = StudentRegistrationUpdate(status=RegistrationStatus.APPROVED)  # type: ignore
        await StudentRegistrationService.update_registration(
            mocked_db_session,
            mock_student_registration.id,
            update_data,
            mock_student_user,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_registration_staff_update_answer_success(
    mocked_db_session: AsyncMock,
    mock_social_worker_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(answer={"new_q": "new_a"})  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session,
        mock_student_registration.id,
        update_data,
        mock_social_worker_user,
    )
    assert updated_registration.answer == {"new_q": "new_a"}
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_staff_update_status_success_no_existing_review(
    mocked_db_session: AsyncMock,
    mock_social_worker_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mock_student_registration.review = None
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(status=RegistrationStatus.APPROVED)  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session,
        mock_student_registration.id,
        update_data,
        mock_social_worker_user,
    )
    assert updated_registration.review.status == RegistrationStatus.APPROVED  # type: ignore
    assert updated_registration.review.student_registration_id == mock_student_registration.id  # type: ignore
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_staff_update_status_success_existing_review(
    mocked_db_session: AsyncMock,
    mock_social_worker_user: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
):
    mock_student_registration.review = mock_review
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    update_data = StudentRegistrationUpdate(status=RegistrationStatus.REJECTED)  # type: ignore
    updated_registration = await StudentRegistrationService.update_registration(
        mocked_db_session,
        mock_student_registration.id,
        update_data,
        mock_social_worker_user,
    )
    assert updated_registration.review.status == RegistrationStatus.REJECTED  # type: ignore
    mocked_db_session.commit.assert_called_once()
    mocked_db_session.refresh.assert_called_once_with(updated_registration)


@pytest.mark.asyncio
async def test_update_registration_not_found(
    mocked_db_session: AsyncMock, mock_social_worker_user: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        update_data = StudentRegistrationUpdate(status=RegistrationStatus.APPROVED)  # type: ignore
        await StudentRegistrationService.update_registration(
            mocked_db_session, 999, update_data, mock_social_worker_user
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_registration_no_permission(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    non_permitted_user = MagicMock(spec=User)
    non_permitted_user.id = 4
    non_permitted_user.user_type = UserType.STUDENT  # But not the owner
    non_permitted_user.is_staff = False
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    with pytest.raises(HTTPException) as exc_info:
        update_data = StudentRegistrationUpdate(answer={"q": "a"})  # type: ignore
        await StudentRegistrationService.update_registration(
            mocked_db_session,
            mock_student_registration.id,
            update_data,
            non_permitted_user,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_registration_student_owner_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    result = await StudentRegistrationService.delete_registration(
        mocked_db_session, mock_student_registration.id, mock_student_user
    )
    assert result is True
    mocked_db_session.delete.assert_called_once_with(mock_student_registration)
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_registration_student_not_owner(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mock_student_registration.student_id = 999  # Not the owner
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    with pytest.raises(HTTPException) as exc_info:
        await StudentRegistrationService.delete_registration(
            mocked_db_session, mock_student_registration.id, mock_student_user
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_registration_staff_success(
    mocked_db_session: AsyncMock,
    mock_social_worker_user: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    result = await StudentRegistrationService.delete_registration(
        mocked_db_session, mock_student_registration.id, mock_social_worker_user
    )
    assert result is True
    mocked_db_session.delete.assert_called_once_with(mock_student_registration)
    mocked_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_registration_not_found(
    mocked_db_session: AsyncMock, mock_social_worker_user: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        await StudentRegistrationService.delete_registration(
            mocked_db_session, 999, mock_social_worker_user
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_registration_no_permission(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
):
    non_permitted_user = MagicMock(spec=User)
    non_permitted_user.id = 4
    non_permitted_user.user_type = UserType.STUDENT  # But not the owner
    non_permitted_user.is_staff = False
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    with pytest.raises(HTTPException) as exc_info:
        await StudentRegistrationService.delete_registration(
            mocked_db_session, mock_student_registration.id, non_permitted_user
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_student_registration_for_notice_success(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_student_registration
    )
    registration = await StudentRegistrationService.get_student_registration_for_notice(
        mocked_db_session, mock_student_user.id, mock_notice.id
    )
    assert registration == mock_student_registration


@pytest.mark.asyncio
async def test_get_student_registration_for_notice_not_found(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None
    registration = await StudentRegistrationService.get_student_registration_for_notice(
        mocked_db_session, mock_student_user.id, mock_notice.id
    )
    assert registration is None


@pytest.mark.asyncio
async def test_get_student_registrations_with_reviews_success_with_review(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
    mock_notice: MagicMock,
):
    mock_student_registration.review = mock_review
    mock_student_registration.notice = mock_notice
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]
    registrations_with_reviews = (
        await StudentRegistrationService.get_student_registrations_with_reviews(
            mocked_db_session, mock_student_user.id
        )
    )
    assert len(registrations_with_reviews) == 1
    assert registrations_with_reviews[0].notice.id == mock_notice.id
    assert registrations_with_reviews[0].review.status == RegistrationStatus.APPROVED  # type: ignore
    assert registrations_with_reviews[0].review.ivs == 50.0  # type: ignore
    assert registrations_with_reviews[0].review.expires_at is not None  # type: ignore


@pytest.mark.asyncio
async def test_get_student_registrations_with_reviews_success_no_review(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
    mock_notice: MagicMock,
):
    mock_student_registration.review = None
    mock_student_registration.notice = mock_notice
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]
    registrations_with_reviews = (
        await StudentRegistrationService.get_student_registrations_with_reviews(
            mocked_db_session, mock_student_user.id
        )
    )
    assert len(registrations_with_reviews) == 1
    assert registrations_with_reviews[0].notice.id == mock_notice.id
    assert registrations_with_reviews[0].review is None


@pytest.mark.asyncio
async def test_get_student_registrations_with_reviews_no_registrations(
    mocked_db_session: AsyncMock, mock_student_user: MagicMock
):
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = []
    registrations_with_reviews = (
        await StudentRegistrationService.get_student_registrations_with_reviews(
            mocked_db_session, mock_student_user.id
        )
    )
    assert len(registrations_with_reviews) == 0


@pytest.mark.asyncio
async def test_get_student_registrations_with_reviews_expires_at_calculation(
    mocked_db_session: AsyncMock,
    mock_student_user: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
    mock_notice: MagicMock,
):
    mock_student_registration.review = mock_review
    mock_student_registration.notice = mock_notice
    mock_notice.registration_end_date = datetime(
        2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc
    )
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    registrations_with_reviews = (
        await StudentRegistrationService.get_student_registrations_with_reviews(
            mocked_db_session, mock_student_user.id
        )
    )
    expected_expires_at = datetime(
        2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc
    )  # 2 years after registration_end_date
    assert registrations_with_reviews[0].review.expires_at == expected_expires_at  # type: ignore


@pytest.mark.asyncio
async def test_get_registrations_for_notice_list_no_filter(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
):
    mock_student_registration.review = mock_review
    mock_student_registration.documents = [
        MagicMock(),
        MagicMock(),
    ]  # Simulate 2 documents
    mocked_db_session.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    response = await StudentRegistrationService.get_registrations_for_notice_list(
        mocked_db_session, mock_notice.id
    )

    assert len(response.registrations) == 1
    assert response.registrations[0].id == mock_student_registration.id
    assert response.registrations[0].review.status == RegistrationStatus.APPROVED.value
    assert response.registrations[0].review.progress == 100
    assert response.registrations[0].review.qtd_document == 2
    assert response.registrations[0].review.reviewer.id == mock_review.social_worker.id  # type: ignore
    assert response.approved_count == 1
    assert response.pending_count == 0


@pytest.mark.asyncio
async def test_get_registrations_for_notice_list_pending_filter(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
):
    mock_student_registration.review = None  # No review, so pending
    mock_student_registration.documents = []
    mocked_db_session.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    response = await StudentRegistrationService.get_registrations_for_notice_list(
        mocked_db_session, mock_notice.id, status=RegistrationStatus.PENDING
    )

    assert len(response.registrations) == 1
    assert response.registrations[0].review.status == RegistrationStatus.PENDING.value
    assert response.pending_count == 1
    assert response.approved_count == 0


@pytest.mark.asyncio
async def test_get_registrations_for_notice_list_approved_filter(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
):
    mock_student_registration.review = mock_review
    mock_student_registration.documents = []
    mocked_db_session.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    response = await StudentRegistrationService.get_registrations_for_notice_list(
        mocked_db_session, mock_notice.id, status=RegistrationStatus.APPROVED
    )

    assert len(response.registrations) == 1
    assert response.registrations[0].review.status == RegistrationStatus.APPROVED.value
    assert response.approved_count == 1
    assert response.pending_count == 0


@pytest.mark.asyncio
async def test_get_registrations_for_notice_list_no_registrations(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.unique.return_value.scalars.return_value.all.return_value = (
        []
    )

    response = await StudentRegistrationService.get_registrations_for_notice_list(
        mocked_db_session, mock_notice.id
    )

    assert len(response.registrations) == 0
    assert response.pending_count == 0
    assert response.approved_count == 0


@pytest.mark.asyncio
async def test_get_registrations_by_notice_no_filter(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
):
    mocked_db_session.execute.return_value.scalar_one.return_value = (
        1  # For count_query
    )
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    registrations, total = await StudentRegistrationService.get_registrations_by_notice(
        mocked_db_session, mock_notice.id
    )

    assert len(registrations) == 1
    assert total == 1
    assert registrations[0] == mock_student_registration


@pytest.mark.asyncio
async def test_get_registrations_by_notice_with_filter(
    mocked_db_session: AsyncMock,
    mock_notice: MagicMock,
    mock_student_registration: MagicMock,
    mock_review: MagicMock,
):
    mock_student_registration.review = mock_review
    mocked_db_session.execute.return_value.scalar_one.return_value = (
        1  # For count_query
    )
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_student_registration
    ]

    registrations, total = await StudentRegistrationService.get_registrations_by_notice(
        mocked_db_session, mock_notice.id, status=RegistrationStatus.APPROVED
    )

    assert len(registrations) == 1
    assert total == 1
    assert registrations[0] == mock_student_registration


@pytest.mark.asyncio
async def test_get_registrations_by_notice_no_registrations(
    mocked_db_session: AsyncMock, mock_notice: MagicMock
):
    mocked_db_session.execute.return_value.scalar_one.return_value = (
        0  # For count_query
    )
    mocked_db_session.execute.return_value.scalars.return_value.all.return_value = []

    registrations, total = await StudentRegistrationService.get_registrations_by_notice(
        mocked_db_session, mock_notice.id
    )

    assert len(registrations) == 0
    assert total == 0
