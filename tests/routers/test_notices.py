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

    # Found the created notice
    assert any(notice["title"] == "Test Notice for Listing" for notice in notices)


@pytest.mark.asyncio
async def test_get_notice_by_id(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test getting a single notice by its ID."""
    notice_data = NoticeCreate(
        title="Test Notice for ID",
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


@pytest.mark.asyncio
async def test_create_notice_as_non_coordinator(
    client: AsyncClient, social_worker_token: str
):
    """Test that a non-coordinator cannot create a notice."""
    notice_data = NoticeCreate(
        title="Invalid Notice",
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
async def test_update_notice_as_coordinator_in_team(
    client: AsyncClient, coordinator_token: str
):
    """Test that a coordinator in the team can update the notice."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    notice_data = NoticeCreate(
        title="Update Test Notice",
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
