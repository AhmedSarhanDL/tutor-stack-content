import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_ingest_content(async_client: AsyncClient):
    # Test ingesting new content
    response = await async_client.post("/ingest", json={"text": "Test content"})
    assert response.status_code == 200
    assert "id" in response.json()
    assert isinstance(response.json()["id"], int)

async def test_search_content(async_client: AsyncClient):
    # First ingest some test content
    await async_client.post("/ingest", json={"text": "Python is a great programming language"})
    await async_client.post("/ingest", json={"text": "FastAPI makes building APIs easy"})
    
    # Test searching content
    response = await async_client.post("/search", json={"text": "Python"}, params={"k": 1})
    assert response.status_code == 200
    assert "chunks" in response.json()
    assert len(response.json()["chunks"]) <= 1  # Should respect k parameter
    assert "Python" in response.json()["chunks"][0]

async def test_search_with_no_results(async_client: AsyncClient):
    # Test searching for non-existent content
    response = await async_client.post("/search", json={"text": "NonexistentContent123"})
    assert response.status_code == 200
    assert "chunks" in response.json()
    assert len(response.json()["chunks"]) == 0

async def test_invalid_input(async_client: AsyncClient):
    # Test invalid input for ingest
    response = await async_client.post("/ingest", json={})
    assert response.status_code == 422  # Validation error

    # Test invalid input for search
    response = await async_client.post("/search", json={})
    assert response.status_code == 422  # Validation error 