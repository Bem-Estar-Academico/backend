import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserType
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """
    Test successful login.
    """
    password = "testpassword"
    user_data = UserCreate(
        email="test-success@example.com",
        full_name="Test User Success",
        user_type=UserType.STUDENT,
        password=password,
        cpf="00000000000",
        registration_number="11111111",
    )
    await UserService.create_user(db_session, user_data)

    login_data = {"username": user_data.email, "password": password}
    response = await client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """
    Test login with wrong password.
    """
    password = "testpassword"
    user_data = UserCreate(
        email="test-wrong-pass@example.com",
        full_name="Test User Wrong Pass",
        user_type=UserType.STUDENT,
        password=password,
        cpf="00000000000",
        registration_number="11111111",
    )
    await UserService.create_user(db_session, user_data)

    login_data = {"username": user_data.email, "password": "wrongpassword"}
    response = await client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    """
    Test login for a user that does not exist.
    """
    login_data = {"username": "nonexistent@example.com", "password": "password"}
    response = await client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 401
