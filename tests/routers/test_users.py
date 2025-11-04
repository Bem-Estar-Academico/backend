from typing import Dict, Any
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserType
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient):
    """Test that an unauthenticated user cannot list users."""
    response = await client.get("/api/v1/users/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_as_student(client: AsyncClient, db_session: AsyncSession):
    """Test that a student user cannot list users."""
    student_password = "studentpassword"
    student_data = UserCreate(
        email="student@example.com",
        full_name="Student User",
        user_type=UserType.STUDENT,
        password=student_password,
        cpf="00000000000",
        registration_number="00000000",
    )
    await UserService.create_user(db_session, student_data)
    login_data = {"username": student_data.email, "password": student_password}
    response = await client.post("/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_coordinator(client: AsyncClient, db_session: AsyncSession):
    """Test that a coordinator can list social worker users."""
    coordinator_password = "coordpassword"
    coordinator_data = UserCreate(
        email="coordinator@example.com",
        full_name="Coordinator User",
        user_type=UserType.COORDINATOR,
        password=coordinator_password,
        cpf=None,
        registration_number=None,
    )
    await UserService.create_user(db_session, coordinator_data)
    social_worker_data = UserCreate(
        email="socialworker@example.com",
        full_name="Social Worker User",
        user_type=UserType.SOCIAL_WORKER,
        password="swpassword",
        cpf=None,
        registration_number=None,
    )
    await UserService.create_user(db_session, social_worker_data)
    login_data = {"username": coordinator_data.email, "password": coordinator_password}
    response = await client.post("/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        "/api/v1/users/?user_type=SOCIAL_WORKER", headers=headers
    )

    assert response.status_code == 200
    users: list[Dict[str, Any]] = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert any(u["email"] == social_worker_data.email for u in users)
    assert all(u["user_type"] == UserType.SOCIAL_WORKER.value for u in users)
