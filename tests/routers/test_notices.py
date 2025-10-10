from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserType
from app.schemas.notice import NoticeCreate, NoticeUpdate
from app.schemas.user import UserCreate
from app.services.notice_service import NoticeService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_list_notices(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test that anyone can list notices."""
    notice_data = NoticeCreate(
        title="Test Notice for Listing",
        notice_number="01/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Test Agency",
        description="This is a test notice.",
    )
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )

    response = await client.get("/api/v1/notices/")
    assert response.status_code == 200
    notices = response.json()
    assert isinstance(notices, list)
    assert len(notices) >= 1
    assert notices[0]["title"] == "Test Notice for Listing"


@pytest.mark.asyncio
async def test_get_notice_by_id(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test getting a single notice by its ID."""
    notice_data = NoticeCreate(
        title="Test Notice for ID",
        notice_number="02/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Test Agency",
        description="This is another test notice.",
    )
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/notices/{notice_id}")
    assert response.status_code == 200
    notice = response.json()
    assert notice["id"] == notice_id
    assert notice["title"] == "Test Notice for ID"


@pytest.mark.asyncio
async def test_get_notice_not_found(client: AsyncClient):
    """Test that getting a notice that does not exist returns a 404 error."""
    response = await client.get("/api/v1/notices/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_notice_as_coordinator(
    client: AsyncClient, coordinator_token: str
):
    """Test that a coordinator can create a notice."""
    notice_data = NoticeCreate(
        title="Coordinator Notice",
        notice_number="03/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Coordinator Agency",
        description="A notice created by a coordinator.",
    )
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    assert response.status_code == 201
    created_notice = response.json()
    assert created_notice["title"] == "Coordinator Notice"
    assert len(created_notice["team_members"]) == 1
    assert created_notice["team_members"][0]["role"] == "COORDINATOR"


@pytest.mark.asyncio
async def test_create_notice_as_non_coordinator(
    client: AsyncClient, social_worker_token: str
):
    """Test that a non-coordinator cannot create a notice."""
    notice_data = NoticeCreate(
        title="Invalid Notice",
        notice_number="04/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Invalid Agency",
        description="This notice should not be created.",
    )
    headers = {"Authorization": f"Bearer {social_worker_token}"}
    response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_active_notices(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test that only active notices are returned."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    # Active notice
    active_notice_data = NoticeCreate(
        title="Active Notice",
        notice_number="05/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc) - timedelta(days=1),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        responsible_agency="Active Agency",
        description="This is an active notice.",
    )
    await client.post(
        "/api/v1/notices/",
        json=active_notice_data.model_dump(mode="json"),
        headers=headers,
    )

    # Inactive notice (in the future)
    future_notice_data = NoticeCreate(
        title="Future Notice",
        notice_number="06/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc) + timedelta(days=5),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Future Agency",
        description="This is a future notice.",
    )
    await client.post(
        "/api/v1/notices/",
        json=future_notice_data.model_dump(mode="json"),
        headers=headers,
    )

    response = await client.get("/api/v1/notices/active")
    assert response.status_code == 200
    active_notices = response.json()
    assert isinstance(active_notices, list)
    assert len(active_notices) >= 1
    assert any(notice["title"] == "Active Notice" for notice in active_notices)
    assert not any(notice["title"] == "Future Notice" for notice in active_notices)


@pytest.mark.asyncio
async def test_get_notices_by_year(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test filtering notices by year."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_2024_data = NoticeCreate(
        title="Notice 2024",
        notice_number="01/2024",
        year=2024,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Agency 2024",
        description="Notice from 2024.",
    )
    await client.post(
        "/api/v1/notices/",
        json=notice_2024_data.model_dump(mode="json"),
        headers=headers,
    )

    response = await client.get("/api/v1/notices/year/2024")
    assert response.status_code == 200
    notices_2024 = response.json()
    assert isinstance(notices_2024, list)
    assert len(notices_2024) >= 1
    assert all(notice["year"] == 2024 for notice in notices_2024)


@pytest.mark.asyncio
async def test_update_notice_as_coordinator_in_team(
    client: AsyncClient, coordinator_token: str
):
    """Test that a coordinator in the team can update the notice."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_data = NoticeCreate(
        title="Update Test Notice",
        notice_number="07/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Update Agency",
        description="Original description.",
    )
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    update_data = NoticeUpdate(
        title="Updated Title",
        notice_number="07/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Update Agency",
        description="Original description.",
        food_allowance=True,
        housing_allowance=False,
        daycare_allowance=True,
        graduation_scholarship=False,
    )
    response = await client.put(
        f"/api/v1/notices/{notice_id}",
        json=update_data.model_dump(mode="json"),
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_notice_as_coordinator_in_team(
    client: AsyncClient, coordinator_token: str
):
    """Test that a coordinator in the team can delete the notice."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_data = NoticeCreate(
        title="Delete Test Notice",
        notice_number="08/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Delete Agency",
        description="This notice will be deleted.",
    )
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/notices/{notice_id}", headers=headers
    )
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/notices/{notice_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_add_team_member(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test adding a team member to a notice."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_data = NoticeCreate(
        title="Team Test Notice",
        notice_number="09/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Team Agency",
        description="A notice for team member tests.",
    )
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    social_worker_password = "swpassword"
    social_worker_data = UserCreate(
        email="sw.fortest@example.com",
        full_name="Social Worker for Test",
        user_type=UserType.SOCIAL_WORKER,
        password=social_worker_password,
    )
    user = await UserService.create_user(db_session, social_worker_data)

    response = await client.post(
        f"/api/v1/notices/{notice_id}/team?user_id={user.id}&role=SOCIAL_WORKER",
        headers=headers,
    )
    assert response.status_code == 200
    team_member = response.json()
    assert team_member["user_id"] == user.id
    assert team_member["role"] == "SOCIAL_WORKER"


@pytest.mark.asyncio
@patch("app.core.s3_manager.s3_manager", new_callable=MagicMock)
async def test_upload_document(
    mock_s3_manager, client: AsyncClient, coordinator_token: str
):
    """Test uploading a document to a notice."""
    mock_s3_manager.upload_file.return_value = "some_file_key"
    mock_s3_manager.generate_presigned_download_url.return_value = (
        "http://example.com/some_file_key"
    )

    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_data = NoticeCreate(
        title="Document Test Notice",
        notice_number="10/2025",
        year=2025,
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        responsible_agency="Document Agency",
        description="A notice for document upload tests.",
    )
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    files = {"file": ("test_document.txt", b"This is a test document.", "text/plain")}
    response = await client.post(
        f"/api/v1/notices/{notice_id}/documents", files=files, headers=headers
    )

    assert response.status_code == 200
    document = response.json()
    assert document["name"] == "test_document.txt"
    assert "file_url" in document
