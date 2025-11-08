from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notice import NoticeCreate, NoticeUpdate


@pytest.mark.asyncio
async def test_list_notices(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test that anyone can list notices."""
    notice_data = NoticeCreate(
        title="Test Notice for Listing",
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
        description="This is a test notice.",
    )
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )

    response = await client.get("/api/v1/notices/", headers=headers)
    assert response.status_code == 200
    notices: List[Dict[str, Any]] = response.json()
    assert isinstance(notices, list)
    assert len(notices) >= 1
    assert any(notice["title"] == "Test Notice for Listing" for notice in notices)


@pytest.mark.asyncio
async def test_get_notice_by_id(
    client: AsyncClient, db_session: AsyncSession, coordinator_token: str
):
    """Test getting a single notice by its ID."""
    notice_data = NoticeCreate(
        title="Test Notice for ID",
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
        description="This is another test notice.",
    )
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/notices/{notice_id}", headers=headers)
    assert response.status_code == 200
    notice = response.json()
    assert notice["id"] == notice_id
    assert notice["title"] == "Test Notice for ID"


@pytest.mark.asyncio
async def test_get_notice_not_found(client: AsyncClient, coordinator_token: str):
    """Test that getting a notice that does not exist returns a 404 error."""
    headers = {"Authorization": f"Bearer {coordinator_token}"}
    response = await client.get("/api/v1/notices/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_notice_as_coordinator(
    client: AsyncClient, coordinator_token: str
):
    """Test that a coordinator can create a notice."""
    notice_data = NoticeCreate(
        title="Coordinator Notice",
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
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
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
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
    active_notice_data = NoticeCreate(
        title="Active Notice",
        registration_start_date=datetime.now(timezone.utc) - timedelta(days=1),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
        description="This is an active notice.",
    )
    await client.post(
        "/api/v1/notices/",
        json=active_notice_data.model_dump(mode="json"),
        headers=headers,
    )

    future_notice_data = NoticeCreate(
        title="Future Notice",
        registration_start_date=datetime.now(timezone.utc) + timedelta(days=5),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
        description="This is a future notice.",
    )
    await client.post(
        "/api/v1/notices/",
        json=future_notice_data.model_dump(mode="json"),
        headers=headers,
    )

    response = await client.get("/api/v1/notices/active", headers=headers)
    assert response.status_code == 200
    active_notices: List[Dict[str, Any]] = response.json()
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
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
        description="Original description.",
    )
    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )
    notice_id = create_response.json()["id"]

    update_data = NoticeUpdate(
        title="Updated Title",
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
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
        registration_start_date=datetime.now(timezone.utc),
        registration_end_date=datetime.now(timezone.utc) + timedelta(days=10),
        appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
        appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
        preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
        final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
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

    get_response = await client.get(f"/api/v1/notices/{notice_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
@patch("app.core.s3_manager.s3_manager", new_callable=MagicMock)
async def test_upload_document(
    mock_s3_manager: MagicMock,
    client: AsyncClient,
    coordinator_token: str,
    tmp_path: Path,
):
    mock_s3_manager.upload_file.return_value = "some_file_key"
    mock_s3_manager.generate_signed_url.return_value = (
        "http://mock-s3-url/some_file_key"
    )

    headers = {"Authorization": f"Bearer {coordinator_token}"}

    now = datetime.now(timezone.utc)
    notice_data = NoticeCreate(
        title="Document Test Notice",
        registration_start_date=now,
        registration_end_date=now + timedelta(days=10),
        appeal_start_date=now + timedelta(days=1),
        appeal_end_date=now + timedelta(days=11),
        preliminary_result_date=now + timedelta(days=12),
        final_result_date=now + timedelta(days=22),
        description="A notice for document upload tests.",
    )

    create_response = await client.post(
        "/api/v1/notices/", json=notice_data.model_dump(mode="json"), headers=headers
    )

    notice_id = create_response.json()["id"]

    mock_file_content = b"Conteudo de teste binario"
    temp_file_path = tmp_path / "cnh.jpg"
    temp_file_path.write_bytes(mock_file_content)

    with open(temp_file_path, "rb") as f:
        files = {"file": ("cnh.jpg", f.read(), "image/jpeg")}
        response = await client.post(
            f"/api/v1/notices/{notice_id}/documents", files=files, headers=headers
        )

    assert response.status_code == 200
    document = response.json()
    assert document["name"] == "cnh.jpg"
    assert "file_key" in document
    assert document["file_url"] == "http://mock-s3-url/some_file_key"

    mock_s3_manager.upload_file.assert_called_once()
