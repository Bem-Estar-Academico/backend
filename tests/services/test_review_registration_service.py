from datetime import datetime, timedelta, timezone
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Notice
from app.models.registration import StudentRegistration
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User, UserType
from app.schemas.review_registration import (
    ReviewRegistrationCreate,
    ReviewRegistrationUpdate,
)
from app.services.review_registration_service import ReviewRegistrationService


@pytest.fixture
def mocked_db_session():
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.execute.return_value = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_social_worker():
    user = MagicMock(spec=User)
    user.is_staff = True
    user.id = 1
    user.user_type = UserType.SOCIAL_WORKER
    return user


@pytest.fixture
def mock_coordinator():
    user = MagicMock(spec=User)
    user.is_staff = True
    user.id = 3
    user.user_type = UserType.COORDINATOR
    return user


@pytest.fixture
def mock_student():
    user = MagicMock(spec=User)
    user.is_staff = False
    user.id = 2
    user.user_type = UserType.STUDENT
    return user


@pytest.fixture
def mock_notice():
    notice = MagicMock(spec=Notice)
    notice.registration_start_date = datetime.now(timezone.utc) - timedelta(days=1)
    notice.registration_end_date = datetime.now(timezone.utc) + timedelta(days=1)
    return notice


@pytest.fixture
def mock_student_registration(mock_notice: MagicMock):
    registration = MagicMock(spec=StudentRegistration)
    registration.id = 1
    registration.notice = mock_notice
    return registration


@pytest.fixture
def mock_review():
    review = MagicMock(spec=ReviewRegistrationModel)
    review.id = 1
    review.student_registration_id = 1
    review.social_worker_id = 1
    review.status = RegistrationStatus.PENDING
    review.ivs = None
    return review


@pytest.mark.asyncio
async def test_create_review_success(
    mocked_db_session: AsyncSession,
    mock_social_worker: User,
    mock_student_registration: StudentRegistration,
) -> None:
    with patch(
        "app.services.student_registration_service.StudentRegistrationService.get_registration_by_id",
        new=AsyncMock(return_value=mock_student_registration),
    ), patch(
        "app.services.review_registration_service.ReviewRegistrationService.get_review_by_student_registration_id",
        new=AsyncMock(return_value=None),
    ):
        review_data: ReviewRegistrationCreate = ReviewRegistrationCreate(
            status=RegistrationStatus.APPROVED,
            review={"comments": "Test comments"},
            ivs=0.0,
            ocr_analisys={},
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        review: ReviewRegistrationModel = await ReviewRegistrationService.create_review(
            mocked_db_session, mock_social_worker, 1, review_data
        )
        assert review is not None
        mocked_db_session.add.assert_called_once()  # type: ignore
        mocked_db_session.commit.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_create_review_not_staff(
    mocked_db_session: AsyncSession, mock_student: User
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        review_data: ReviewRegistrationCreate = ReviewRegistrationCreate(
            status=RegistrationStatus.APPROVED,
            review={"comments": "Test comments"},
            ivs=0.0,
            ocr_analisys={},
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.create_review(
            mocked_db_session, mock_student, 1, review_data
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_review_registration_not_found(
    mocked_db_session: AsyncSession, mock_social_worker: User
) -> None:
    with patch(
        "app.services.student_registration_service.StudentRegistrationService.get_registration_by_id",
        new=AsyncMock(return_value=None),
    ), pytest.raises(HTTPException) as exc_info:
        review_data: ReviewRegistrationCreate = ReviewRegistrationCreate(
            status=RegistrationStatus.APPROVED,
            review={"comments": "Test comments"},
            ivs=0.0,
            ocr_analisys={},
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.create_review(
            mocked_db_session, mock_social_worker, 1, review_data
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_review_already_exists(
    mocked_db_session: AsyncSession,
    mock_social_worker: User,
    mock_student_registration: StudentRegistration,
) -> None:
    with patch(
        "app.services.student_registration_service.StudentRegistrationService.get_registration_by_id",
        new=AsyncMock(return_value=mock_student_registration),
    ), patch(
        "app.services.review_registration_service.ReviewRegistrationService.get_review_by_student_registration_id",
        new=AsyncMock(return_value=MagicMock()),
    ), pytest.raises(
        HTTPException
    ) as exc_info:
        review_data: ReviewRegistrationCreate = ReviewRegistrationCreate(
            status=RegistrationStatus.APPROVED,
            review={"comments": "Test comments"},
            ivs=0.0,
            ocr_analisys={},
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.create_review(
            mocked_db_session, mock_social_worker, 1, review_data
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_review_by_id_success(
    mocked_db_session: AsyncSession, mock_review: ReviewRegistrationModel
) -> None:
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = mock_review  # type: ignore
    review: ReviewRegistrationModel | None = (
        await ReviewRegistrationService.get_review_by_id(mocked_db_session, 1)
    )
    assert review == mock_review
    mocked_db_session.execute.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_get_review_by_id_not_found(mocked_db_session: AsyncSession) -> None:
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None  # type: ignore
    review: ReviewRegistrationModel | None = (
        await ReviewRegistrationService.get_review_by_id(mocked_db_session, 1)
    )
    assert review is None
    mocked_db_session.execute.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_get_review_by_student_registration_id_success(
    mocked_db_session: AsyncSession, mock_review: ReviewRegistrationModel
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_review
    mocked_db_session.execute.return_value = result  # type: ignore
    review: ReviewRegistrationModel | None = (
        await ReviewRegistrationService.get_review_by_student_registration_id(
            mocked_db_session, 1
        )
    )
    assert review == mock_review
    mocked_db_session.execute.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_get_review_by_student_registration_id_not_found(
    mocked_db_session: AsyncSession,
) -> None:
    mocked_db_session.execute.return_value.scalar_one_or_none.return_value = None  # type: ignore
    review: ReviewRegistrationModel | None = (
        await ReviewRegistrationService.get_review_by_student_registration_id(
            mocked_db_session, 1
        )
    )
    assert review is None
    mocked_db_session.execute.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_update_review_success_approved_no_appeal(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_social_worker: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ):
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPROVED,
            ivs=50.0,
            appeal=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        with patch(
            "app.schemas.review_registration.ReviewRegistrationUpdate.calculate_ivs",
            return_value=50.0,
        ):
            updated_review: ReviewRegistrationModel | None = (
                await ReviewRegistrationService.update_review(
                    mocked_db_session, 1, update_data, mock_social_worker
                )
            )
        assert updated_review is not None
        assert updated_review.status == RegistrationStatus.APPROVED
        assert updated_review.ivs == 50.0
        mocked_db_session.commit.assert_called_once()  # type: ignore
        mocked_db_session.refresh.assert_called_once_with(mock_review)  # type: ignore


@pytest.mark.asyncio
async def test_update_review_permission_denied(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_student: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ), pytest.raises(HTTPException) as exc_info:
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPROVED,
            ivs=50.0,
            appeal=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.update_review(
            mocked_db_session, 1, update_data, mock_student
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_review_not_found(
    mocked_db_session: AsyncSession, mock_social_worker: User
) -> None:
    with patch.object(
        ReviewRegistrationService, "get_review_by_id", new=AsyncMock(return_value=None)
    ):
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPROVED,
            ivs=50.0,
            appeal=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        updated_review: ReviewRegistrationModel | None = (
            await ReviewRegistrationService.update_review(
                mocked_db_session, 1, update_data, mock_social_worker
            )
        )
        assert updated_review is None


@pytest.mark.asyncio
async def test_update_review_approved_with_appeal_data_fails(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_social_worker: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ), pytest.raises(HTTPException) as exc_info:
        appeal_data: Dict[str, str] = {
            "rg_frente": "Reenvie a foto com melhor iluminação.",
            "comprovante_residencia": "Documento ilegível.",
        }
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPROVED,
            appeal=appeal_data,
            ivs=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.update_review(
            mocked_db_session, 1, update_data, mock_social_worker
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_review_appeal_without_appeal_data(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_social_worker: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ), pytest.raises(HTTPException) as exc_info:
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPEAL,
            appeal=None,
            ivs=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.update_review(
            mocked_db_session, 1, update_data, mock_social_worker
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_review_appeal_success(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_social_worker: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ), patch(
        "app.services.appeal_service.AppealService.create_appeal",
        new=AsyncMock(return_value=MagicMock()),
    ) as mock_create_appeal:
        appeal_data: Dict[str, str] = {
            "rg_frente": "Reenvie a foto com melhor iluminação.",
            "comprovante_residencia": "Documento ilegível.",
        }
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPEAL,
            appeal=appeal_data,
            ivs=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        updated_review: ReviewRegistrationModel | None = (
            await ReviewRegistrationService.update_review(
                mocked_db_session, 1, update_data, mock_social_worker
            )
        )
        assert updated_review is not None
        assert updated_review.status == RegistrationStatus.APPEAL
        mock_create_appeal.assert_called_once()
        mocked_db_session.commit.assert_called_once()  # type: ignore
        mocked_db_session.refresh.assert_called_once_with(mock_review)  # type: ignore


@pytest.mark.asyncio
async def test_update_review_internal_error_on_appeal_create(
    mocked_db_session: AsyncSession,
    mock_review: ReviewRegistrationModel,
    mock_social_worker: User,
) -> None:
    with patch.object(
        ReviewRegistrationService,
        "get_review_by_id",
        new=AsyncMock(return_value=mock_review),
    ), patch(
        "app.services.appeal_service.AppealService.create_appeal",
        new=AsyncMock(side_effect=Exception("DB Error")),
    ), pytest.raises(
        HTTPException
    ) as exc_info:
        appeal_data: Dict[str, str] = {
            "rg_frente": "Reenvie a foto com melhor iluminação.",
            "comprovante_residencia": "Documento ilegível.",
        }
        update_data: ReviewRegistrationUpdate = ReviewRegistrationUpdate(
            status=RegistrationStatus.APPEAL,
            appeal=appeal_data,
            ivs=None,
            review=None,
            approved_food_allowance=False,
            approved_housing_allowance=False,
            approved_daycare_allowance=False,
            approved_graduation_scholarship=False,
        )
        await ReviewRegistrationService.update_review(
            mocked_db_session, 1, update_data, mock_social_worker
        )
    assert exc_info.value.status_code == 500
