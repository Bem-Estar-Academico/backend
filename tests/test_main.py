from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "BEA API"
