import os
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

# Set dummy env vars before importing app settings
os.environ.setdefault("API_KEY", "test-secret-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from app.core.config import settings
from app.main import app
from app.services import llm_service

client = TestClient(app)
VALID_HEADERS = {"X-API-Key": settings.API_KEY}


@pytest.fixture(autouse=True)
def reset_cache_and_mock_gemini(monkeypatch):
    """Clears TTL cache and mocks Gemini streaming so tests run offline."""
    llm_service.prompt_cache.clear()

    async def fake_generate_content_stream(model: str, contents: str):
        async def _token_generator():
            yield SimpleNamespace(text="Hello ")
            yield SimpleNamespace(text="from mocked Gemini!")

        return _token_generator()

    monkeypatch.setattr(
        llm_service.client.aio.models,
        "generate_content_stream",
        fake_generate_content_stream,
    )


def test_health_and_process_time_header():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert "x-process-time" in res.headers


def test_chat_ui_served_at_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_rejects_missing_or_invalid_api_key():
    res_missing = client.post("/api/v1/chat/stream", json={"prompt": "hi"})
    assert res_missing.status_code == 403

    res_wrong = client.post(
        "/api/v1/chat/stream",
        headers={"X-API-Key": "wrong-key"},
        json={"prompt": "hi"},
    )
    assert res_wrong.status_code == 403


def test_sse_streaming_and_ttl_cache():
    payload = {"prompt": "Explain caching"}

    # 1st request -> MISS
    res1 = client.post("/api/v1/chat/stream", headers=VALID_HEADERS, json=payload)
    assert res1.status_code == 200
    assert res1.headers["x-cache"] == "MISS"
    assert 'data: "Hello "' in res1.text
    assert 'data: "from mocked Gemini!"' in res1.text
    assert "data: [DONE]" in res1.text

    # 2nd identical request -> HIT
    res2 = client.post("/api/v1/chat/stream", headers=VALID_HEADERS, json=payload)
    assert res2.status_code == 200
    assert res2.headers["x-cache"] == "HIT"
    assert 'data: "Hello from mocked Gemini!"' in res2.text


def test_rate_limit_enforced_after_five_requests():
    statuses = []
    for _ in range(6):
        res = client.post(
            "/api/v1/chat/stream",
            headers=VALID_HEADERS,
            json={"prompt": "Explain caching"},
        )
        statuses.append(res.status_code)

    assert 429 in statuses