from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm import LLMService, get_llm_service


def _fake_completion(text: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


@pytest.fixture
def llm_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    service = LLMService(api_key="test-key", model="test-model")
    service._client.chat.completions.create = MagicMock(  # type: ignore[method-assign]
        return_value=_fake_completion("hello from groq")
    )
    app = create_app()
    app.dependency_overrides[get_llm_service] = lambda: service
    with TestClient(app) as c:
        c.fake_create = service._client.chat.completions.create  # type: ignore[attr-defined]
        yield c


def test_chat_returns_reply(llm_client: TestClient) -> None:
    resp = llm_client.post("/api/v1/chat", json={"prompt": "hi", "system": "be brief"})
    assert resp.status_code == 200
    assert resp.json() == {"reply": "hello from groq", "model": "test-model"}

    kwargs = llm_client.fake_create.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["model"] == "test-model"
    assert kwargs["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ]


def test_chat_rejects_empty_prompt(llm_client: TestClient) -> None:
    resp = llm_client.post("/api/v1/chat", json={"prompt": ""})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_missing_api_key_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ignore the real environment and .env so this never reaches Groq.
    unconfigured = Settings(_env_file=None, groq_api_key=None)
    monkeypatch.setattr("app.services.llm.get_settings", lambda: unconfigured)
    get_llm_service.cache_clear()
    try:
        app = create_app()
        with TestClient(app) as c:
            resp = c.post("/api/v1/chat", json={"prompt": "hi"})
    finally:
        get_llm_service.cache_clear()
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "llm_not_configured"
