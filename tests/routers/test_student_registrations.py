"""Tests for the student registration routes."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Notice
from app.models.registration import StudentRegistration
from app.models.review import ReviewRegistrationModel, RegistrationStatus
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.fixture
async def notice_instance(db_session: AsyncSession) -> Notice:
    """Create a notice directly in the DB."""
    notice = Notice(
        title="Notice for Get Test",
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        description="A notice for get test.",
    )
    db_session.add(notice)
    await db_session.commit()
    await db_session.refresh(notice)
    return notice


@pytest.fixture
async def student_user(db_session: AsyncSession) -> User:
    """Create a student user directly in the DB and return the User object."""
    user = await UserService.get_user_by_email(db_session, "student.test@example.com")
    if user:
        user.is_active = True
        await db_session.commit()
        await db_session.refresh(user)
        return user

    user_data = UserCreate(
        email="student.test@example.com",
        full_name="Test Student",
        user_type=UserType.STUDENT,
        password="studentpassword",
        registration_number="20240001",
        cpf="111.222.333-44",
    )
    created_user = await UserService.create_user(db_session, user_data)
    return created_user


@pytest.fixture
async def other_student_user(db_session: AsyncSession) -> User:
    """Create a second student user for permission testing."""
    user = await UserService.get_user_by_email(db_session, "other.student@example.com")
    if user:
        return user

    user_data = UserCreate(
        email="other.student@example.com",
        full_name="Other Student",
        user_type=UserType.STUDENT,
        password="otherpassword",
        registration_number="20249999",
        cpf="999.888.777-66",
    )
    created_user = await UserService.create_user(db_session, user_data)
    return created_user


@pytest.fixture
async def social_worker_user(db_session: AsyncSession) -> User:
    """Create a social_worker user directly in the DB and return the User object."""
    user = await UserService.get_user_by_email(
        db_session, "social_worker.test@example.com"
    )
    if user:
        user.is_active = True
        await db_session.commit()
        await db_session.refresh(user)
        return user

    user_data = UserCreate(
        email="social_worker.test@example.com",
        full_name="Test Social Worker",
        user_type=UserType.SOCIAL_WORKER,
        password="social_workerpassword",
    )  # type: ignore
    created_user = await UserService.create_user(db_session, user_data)
    return created_user


@pytest.fixture
async def student_token(
    client: AsyncClient, db_session: AsyncSession, student_user: User
) -> str:
    """Create a student user and return an auth token."""
    password = "studentpassword"
    login_data = {"username": student_user.email, "password": password}
    response = await client.post("/api/v1/auth/login", data=login_data)
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_student_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    coordinator_token: str,
    student_token: str,
    social_worker_user: User,
):
    """Test creating a student registration successfully."""
    notice_data = NoticeCreate(
        title="Notice for Registration Test",
        registration_start_date=datetime.now(timezone.utc) - timedelta(days=1),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        description="A notice to test student registration.",
        appeal_end_date=None,
        appeal_start_date=None,
        preliminary_result_date=None,
        final_result_date=None,
        food_allowance=False,
        housing_allowance=False,
        daycare_allowance=False,
        graduation_scholarship=False,
    )
    headers_coord = {"Authorization": f"Bearer {coordinator_token}"}
    create_notice_response = await client.post(
        "/api/v1/notices/",
        json=notice_data.model_dump(mode="json"),
        headers=headers_coord,
    )
    assert create_notice_response.status_code == 201
    notice_id = create_notice_response.json()["id"]

    registration_data: Dict[str, Any] = {
        "answer": {
            "a": ["Answer 1", "Answer 2", "Answer 3", "Answer 4", "Answer 5"],
            "b": "Detailed answer text.",
        },
        "requested_food_allowance": False,
        "requested_housing_allowance": False,
        "requested_daycare_allowance": False,
        "requested_graduation_scholarship": False,
    }
    headers_student = {"Authorization": f"Bearer {student_token}"}

    response = await client.post(
        f"/api/v1/student-registrations/{notice_id}",
        json=registration_data,
        headers=headers_student,
    )

    assert response.status_code == 201
    registration = response.json()
    assert registration["notice_id"] == notice_id


@pytest.mark.asyncio
async def test_get_student_registration_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test getting a student registration by ID successfully."""
    registration = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/{registration.id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == registration.id
    assert data["notice"]["title"] == notice_instance.title


@pytest.mark.asyncio
async def test_student_can_delete_own_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test that a student can delete their own registration."""
    registration = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)
    registration_id = registration.id

    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.delete(
        f"/api/v1/student-registrations/{registration_id}",
        headers=headers,
    )

    assert response.status_code == 204
    deleted_reg = await db_session.get(StudentRegistration, registration_id)
    assert deleted_reg is None


@pytest.mark.asyncio
async def test_student_cannot_delete_other_student_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    other_student_user: User,
    student_token: str,
):
    """Test that a student cannot delete another student's registration."""
    registration = StudentRegistration(
        student_id=other_student_user.id,
        notice_id=notice_instance.id,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)
    registration_id = registration.id

    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.delete(
        f"/api/v1/student-registrations/{registration_id}",
        headers=headers,
    )

    assert response.status_code == 403
    assert "Você só pode deletar suas próprias inscrições" in response.json()["detail"]
    not_deleted_reg = await db_session.get(StudentRegistration, registration_id)
    assert not_deleted_reg is not None


@pytest.mark.asyncio
async def test_list_registrations_by_notice_as_coordinator(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    other_student_user: User,
    coordinator_token: str,
):
    """Test that a coordinator can list all registrations for a notice."""
    db_session.add_all(
        [
            StudentRegistration(
                student_id=student_user.id, notice_id=notice_instance.id
            ),
            StudentRegistration(
                student_id=other_student_user.id, notice_id=notice_instance.id
            ),
        ]
    )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/notice/{notice_instance.id}",
        headers=headers,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "pending_count" in response_data
    assert response_data["pending_count"] == 2
    assert len(response_data["registrations"]) == 2
    student_ids_in_response = {
        reg["student"]["id"] for reg in response_data["registrations"]
    }
    assert {student_user.id, other_student_user.id} == student_ids_in_response


@pytest.mark.asyncio
async def test_list_registrations_by_notice_as_student_fails(
    client: AsyncClient,
    notice_instance: Notice,
    student_token: str,
):
    """Test that a student cannot list registrations for a notice."""
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/notice/{notice_instance.id}",
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_registrations_by_student_as_self(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test that a student can list their own registrations."""
    db_session.add(
        StudentRegistration(student_id=student_user.id, notice_id=notice_instance.id)
    )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/student/{student_user.id}",
        headers=headers,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total"] == 1
    assert len(response_data["registrations"]) == 1
    assert response_data["registrations"][0]["student"]["id"] == student_user.id


@pytest.mark.asyncio
async def test_list_registrations_by_student_as_other_student_fails(
    client: AsyncClient,
    other_student_user: User,
    student_token: str,
):
    """Test that a student cannot list another student's registrations."""
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/student/{other_student_user.id}",
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_registrations_by_notice(
    client: AsyncClient,
    db_session: AsyncSession,
    coordinator_token: str,
    notice_instance: Notice,
    student_user: User,
    other_student_user: User,
    social_worker_user: User,
):
    """
    Test the GET /student-registrations/notice/{notice_id} endpoint with the new response format.
    """
    reg1 = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(reg1)
    await db_session.commit()
    await db_session.refresh(reg1)

    review1 = ReviewRegistrationModel(
        student_registration_id=reg1.id,
        social_worker_id=social_worker_user.id,
        status=RegistrationStatus.APPROVED,
        ivs=80.5,
    )
    db_session.add(review1)

    reg2 = StudentRegistration(
        student_id=other_student_user.id,
        notice_id=notice_instance.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(reg2)

    await db_session.commit()

    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/notice/{notice_instance.id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["pending_count"] == 1
    assert data["approved_count"] == 1
    assert data["rejected_count"] == 0
    assert data["review_count"] == 0
    assert data["appeal_count"] == 0
    assert data["cancelled_count"] == 0
    assert len(data["registrations"]) == 2

    approved_reg_response = next(
        (r for r in data["registrations"] if r["id"] == reg1.id), None
    )
    pending_reg_response = next(
        (r for r in data["registrations"] if r["id"] == reg2.id), None
    )

    assert approved_reg_response is not None
    assert pending_reg_response is not None

    assert approved_reg_response["student"]["id"] == student_user.id
    assert approved_reg_response["student"]["name"] == "Test Student"
    assert approved_reg_response["student"]["cpf"] == "111.222.333-44"
    assert approved_reg_response["review"]["status"] == "APPROVED"
    assert approved_reg_response["review"]["progress"] == 100
    assert approved_reg_response["review"]["reviewer"]["id"] == social_worker_user.id
    assert approved_reg_response["review"]["reviewer"]["name"] == "Test Social Worker"

    assert pending_reg_response["student"]["id"] == other_student_user.id
    assert pending_reg_response["student"]["name"] == "Other Student"
    assert pending_reg_response["review"]["status"] == "PENDING"
    assert pending_reg_response["review"]["progress"] == 25
    assert pending_reg_response["review"]["reviewer"] is None


@pytest.mark.asyncio
async def test_update_review_status_by_coordinator(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    social_worker_user: User,
    coordinator_token: str,
):
    """Test that a coordinator can update a review's status."""
    registration = StudentRegistration(
        student_id=student_user.id, notice_id=notice_instance.id
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    review = ReviewRegistrationModel(
        student_registration_id=registration.id,
        social_worker_id=social_worker_user.id,
        status=RegistrationStatus.PENDING,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    update_data = {"status": RegistrationStatus.APPROVED.value}
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/reviews/{review.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == review.id
    assert response_data["status"] == RegistrationStatus.APPROVED.value

    await db_session.refresh(review)
    assert review.status == RegistrationStatus.APPROVED


@pytest.mark.asyncio
async def test_update_review_status_by_student_to_cancelled_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    social_worker_user: User,
    student_token: str,
):
    """Test that a student cannot cancel a review directly."""
    registration = StudentRegistration(
        student_id=student_user.id, notice_id=notice_instance.id
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    review = ReviewRegistrationModel(
        student_registration_id=registration.id,
        social_worker_id=social_worker_user.id,
        status=RegistrationStatus.PENDING,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    update_data = {"status": RegistrationStatus.CANCELLED.value}
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/reviews/{review.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_review_status_by_student_to_approved_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    social_worker_user: User,
    student_token: str,
):
    """Test that a student CANNOT change a review status to anything."""
    registration = StudentRegistration(
        student_id=student_user.id, notice_id=notice_instance.id
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    review = ReviewRegistrationModel(
        student_registration_id=registration.id,
        social_worker_id=social_worker_user.id,
        status=RegistrationStatus.PENDING,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    update_data = {"status": RegistrationStatus.APPROVED.value}
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/reviews/{review.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_can_cancel_own_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test that a student can cancel their own registration."""
    registration = StudentRegistration(
        student_id=student_user.id, notice_id=notice_instance.id
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    update_data = {"status": RegistrationStatus.CANCELLED.value}
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/{registration.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(StudentRegistration)
        .filter_by(id=registration.id)
        .options(selectinload(StudentRegistration.review))
    )
    updated_registration = result.scalar_one()

    assert updated_registration.review is not None
    assert updated_registration.review.status == RegistrationStatus.CANCELLED


@pytest.mark.asyncio
async def test_update_status_creates_review(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    coordinator_token: str,
):
    """Test that updating status creates a review if one doesn't exist."""
    registration = StudentRegistration(
        student_id=student_user.id, notice_id=notice_instance.id
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    update_data = {"status": RegistrationStatus.REVIEW.value}
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/{registration.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(StudentRegistration)
        .filter_by(id=registration.id)
        .options(selectinload(StudentRegistration.review))
    )
    updated_registration = result.scalar_one()

    assert updated_registration.review is not None
    assert updated_registration.review.status == RegistrationStatus.REVIEW


@pytest.mark.asyncio
async def test_list_registrations_by_notice_with_status_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    other_student_user: User,
    coordinator_token: str,
    social_worker_user: User,
):
    """Test filtering registrations by status for a notice."""
    # Registration 1: Approved
    reg1 = StudentRegistration(student_id=student_user.id, notice_id=notice_instance.id)
    db_session.add(reg1)
    await db_session.commit()
    review1 = ReviewRegistrationModel(
        student_registration_id=reg1.id,
        status=RegistrationStatus.APPROVED,
        social_worker_id=social_worker_user.id,
    )
    db_session.add(review1)

    # Registration 2: Pending (no review object)
    reg2 = StudentRegistration(
        student_id=other_student_user.id, notice_id=notice_instance.id
    )
    db_session.add(reg2)

    await db_session.commit()

    headers = {"Authorization": f"Bearer {coordinator_token}"}
    # Filter for APPROVED status
    response = await client.get(
        f"/api/v1/student-registrations/notice/{notice_instance.id}?status=APPROVED",
        headers=headers,
    )

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["registrations"]) == 1
    assert response_data["registrations"][0]["id"] == reg1.id
    assert response_data["approved_count"] == 1
    assert response_data["pending_count"] == 0  # Because we are filtering
