"""Tests for the student registration routes."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Notice, StudentRegistration
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate
from app.schemas.user import UserCreate
from tests.conftest import create_user_and_token


@pytest.fixture
async def notice_instance(db_session: AsyncSession) -> Notice:
    """Create a notice directly in the DB."""
    notice = Notice(
        title="Notice for Get Test",
        notice_number="12/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        responsible_agency="Test Agency",
        description="A notice for get test.",
    )
    db_session.add(notice)
    await db_session.commit()
    await db_session.refresh(notice)
    return notice


@pytest.fixture
async def student_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Create a student user and return an auth token."""
    password = "studentpassword"
    user_data = UserCreate(
        email="student.test@example.com",
        full_name="Test Student",
        user_type=UserType.STUDENT,
        password=password,
        student_registration="20240001",
        cpf="111.222.333-44",
    )
    return await create_user_and_token(client, db_session, user_data, password)


@pytest.mark.asyncio
async def test_create_student_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    coordinator_token: str,
    student_token: str,
):
    """
    Test creating a student registration.
    This test is expected to FAIL due to the bug in date field names
    (AttributeError: 'Notice' object has no attribute 'start_date').
    When the bug is fixed, this test should pass.
    """
    # 1. Create a notice as a coordinator
    notice_data = NoticeCreate(
        title="Notice for Registration Test",
        notice_number="11/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc) - timedelta(days=1),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        responsible_agency="Test Agency",
        description="A notice to test student registration.",
    )
    headers_coord = {"Authorization": f"Bearer {coordinator_token}"}
    create_notice_response = await client.post(
        "/api/v1/notices/",
        json=notice_data.model_dump(mode="json"),
        headers=headers_coord,
    )
    assert create_notice_response.status_code == 201
    notice_id = create_notice_response.json()["id"]

    # 2. As a student, attempt to register for the notice
    registration_data = {"notice_id": notice_id}
    headers_student = {"Authorization": f"Bearer {student_token}"}

    response = await client.post(
        "/api/v1/registrations/",
        json=registration_data,
        headers=headers_student,
    )

    # This assertion will fail. Expected 201, but will get 500 Internal Server Error.
    assert response.status_code == 201

    registration = response.json()
    assert registration["notice_id"] == notice_id
    assert registration["status"] == "PENDING"


@pytest.mark.asyncio
async def test_get_student_registration_fails_due_to_schema_bug(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_token: str,
):
    """
    Test getting a student registration by ID.
    This test is expected to FAIL due to a Pydantic validation error because
    the 'notice_title' field is missing from the response.
    """
    # 1. Get the user associated with the token
    user_query = select(User).where(User.email == "student.test@example.com")
    user_result = await db_session.execute(user_query)
    token_user = user_result.scalar_one()

    # 2. Create a registration directly in the database for the token user
    registration = StudentRegistration(
        student_id=token_user.id,
        notice_id=notice_instance.id,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    # 3. Attempt to fetch the registration
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/registrations/{registration.id}",
        headers=headers,
    )

    # This assertion will fail. Expected 200, but will get 500 Internal Server Error.
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == registration.id
    assert data["notice"]["title"] == notice_instance.title
