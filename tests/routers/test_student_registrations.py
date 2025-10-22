"""Tests for the student registration routes."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Notice, RegistrationStatus, StudentRegistration
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
        # Corrigido: Removidos os campos 'year' e 'responsible_agency'
        # que não existem no modelo Notice.
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
        student_registration="20240001",
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
        student_registration="20249999",
        cpf="999.888.777-66",
    )
    created_user = await UserService.create_user(db_session, user_data)
    return created_user


@pytest.fixture
async def student_token(client: AsyncClient, db_session: AsyncSession, student_user: User) -> str:
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
):
    """Test creating a student registration successfully."""
    notice_data = NoticeCreate(
        title="Notice for Registration Test",
        registration_start_date=datetime.now(timezone.utc) - timedelta(days=1),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        description="A notice to test student registration.",
        # Corrigido: Removidos os campos 'year' e 'responsible_agency'
        # que não existem no modelo Notice (e presumivelmente no NoticeCreate).
    )
    headers_coord = {"Authorization": f"Bearer {coordinator_token}"}
    create_notice_response = await client.post(
        "/api/v1/notices/",
        json=notice_data.model_dump(mode="json"),
        headers=headers_coord,
    )
    assert create_notice_response.status_code == 201
    notice_id = create_notice_response.json()["id"]
    registration_data = {"notice_id": notice_id}
    headers_student = {"Authorization": f"Bearer {student_token}"}

    response = await client.post(
        "/api/v1/student-registrations/",
        json=registration_data,
        headers=headers_student,
    )

    assert response.status_code == 201

    registration = response.json()
    assert registration["notice_id"] == notice_id
    assert registration["status"] == "PENDENTE"


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
async def test_update_registration_status_by_coordinator(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    coordinator_token: str,
):
    """Test that a coordinator can update a registration's status."""
    registration = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
        status=RegistrationStatus.PENDING,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    assert registration.status == RegistrationStatus.PENDING

    update_data = {"status": RegistrationStatus.APPROVED.value}
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/{registration.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == registration.id
    assert response_data["status"] == RegistrationStatus.APPROVED.value

    await db_session.refresh(registration)
    assert registration.status == RegistrationStatus.APPROVED


@pytest.mark.asyncio
async def test_update_registration_status_by_student_to_cancelled(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test that a student can cancel their own registration."""
    registration = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
        status=RegistrationStatus.PENDING,
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
    response_data = response.json()
    assert response_data["status"] == RegistrationStatus.CANCELLED.value

    await db_session.refresh(registration)
    assert registration.status == RegistrationStatus.CANCELLED


@pytest.mark.asyncio
async def test_update_registration_status_by_student_to_approved_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    notice_instance: Notice,
    student_user: User,
    student_token: str,
):
    """Test that a student CANNOT change their registration status to anything other than CANCELLED."""
    registration = StudentRegistration(
        student_id=student_user.id,
        notice_id=notice_instance.id,
        status=RegistrationStatus.PENDING,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    update_data = {"status": RegistrationStatus.APPROVED.value}
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.put(
        f"/api/v1/student-registrations/{registration.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 403
    assert "Estudantes só podem cancelar suas inscrições" in response.json()["detail"]

    await db_session.refresh(registration)
    assert registration.status == RegistrationStatus.PENDING


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
    student_token: str,  # Token for the first student
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
    # 1. Create a couple of registrations for the notice
    db_session.add_all([
        StudentRegistration(student_id=student_user.id, notice_id=notice_instance.id),
        StudentRegistration(student_id=other_student_user.id, notice_id=notice_instance.id),
    ])
    await db_session.commit()

    # 2. As a coordinator, list the registrations
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/notice/{notice_instance.id}",
        headers=headers,
    )

    # 3. Assert the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total"] == 2
    assert len(response_data["registrations"]) == 2
    student_ids_in_response = {reg["student"]["id"] for reg in response_data["registrations"]}
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
    # 1. Create a registration for the student
    db_session.add(StudentRegistration(student_id=student_user.id, notice_id=notice_instance.id))
    await db_session.commit()

    # 2. As the student, list their registrations
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/student/{student_user.id}",
        headers=headers,
    )

    # 3. Assert the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total"] == 1
    assert len(response_data["registrations"]) == 1
    assert response_data["registrations"][0]["student"]["id"] == student_user.id


@pytest.mark.asyncio
async def test_list_registrations_by_student_as_other_student_fails(
    client: AsyncClient,
    other_student_user: User,
    student_token: str,  # Token for the first student
):
    """Test that a student cannot list another student's registrations."""
    # As the first student, attempt to list the other student's registrations
    headers = {"Authorization": f"Bearer {student_token}"}
    response = await client.get(
        f"/api/v1/student-registrations/student/{other_student_user.id}",
        headers=headers,
    )
    assert response.status_code == 403