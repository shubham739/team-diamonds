"""Tests for OpenRouter client environment-variable behavior."""

import os
from types import SimpleNamespace
from typing import Any

import pytest
import requests
from fastapi import HTTPException
from llm_integration_api.interface.exceptions import LLMIntegrationError

from jira_service import ai_client_api

pytestmark = [pytest.mark.unit, pytest.mark.circleci]


class _FakeBaseOpenRouterClient:
    """Test double for the external OpenRouter client."""

    BASE_URL = "https://example.invalid/chat/completions"

    def __init__(self, api_key: str, model: str, site_url: str = "", app_name: str = "") -> None:
        self.api_key = api_key
        self.model = model
        self.site_url = site_url
        self.app_name = app_name


def test_openrouter_client_persists_api_key_in_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRouterClient should persist the resolved API key in OPENROUTER_API_KEY."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(ai_client_api, "BaseOpenRouterClient", _FakeBaseOpenRouterClient)

    _ = ai_client_api.OpenRouterClient(api_key="test-openrouter-key", model="openai/gpt-4o-mini")

    assert os.environ["OPENROUTER_API_KEY"] == "test-openrouter-key"


def test_jira_mode_requested_detects_explicit_trigger() -> None:
    """Jira tools should only be enabled when the user explicitly uses @jira."""
    assert ai_client_api.jira_mode_requested("@jira tell me about my issues") is True
    assert ai_client_api.jira_mode_requested("Can you tell me the weather?") is False


def test_normalize_chat_message_removes_jira_trigger() -> None:
    """The Jira trigger token should be stripped before sending text to the LLM."""
    assert ai_client_api.normalize_chat_message("@jira list my todo issues") == "list my todo issues"
    assert ai_client_api.normalize_chat_message("What is the weather today?") == "What is the weather today?"


def test_openrouter_client_raises_when_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client creation should fail when no API key is available anywhere."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ai_client_api.OpenRouterError, match="OpenRouter not configured"):
        ai_client_api.OpenRouterClient(api_key="")


def test_openrouter_client_wraps_base_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM integration errors should be wrapped into OpenRouterError."""

    class _BrokenBaseClient:
        BASE_URL = "https://example.invalid/chat/completions"

        def __init__(self, api_key: str, model: str, site_url: str = "", app_name: str = "") -> None:
            del api_key, model, site_url, app_name
            msg = "bad client config"
            raise LLMIntegrationError(msg)

    monkeypatch.setattr(ai_client_api, "BaseOpenRouterClient", _BrokenBaseClient)

    with pytest.raises(ai_client_api.OpenRouterError, match="bad client config"):
        ai_client_api.OpenRouterClient(api_key="test-key")


def test_complete_posts_payload_and_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete() should send the expected payload and return response JSON."""
    monkeypatch.setattr(ai_client_api, "BaseOpenRouterClient", _FakeBaseOpenRouterClient)
    sent: dict[str, Any] = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> dict[str, Any]:
            return {"id": "resp-123", "choices": []}

    def _fake_post(url: str, json: dict[str, Any], headers: dict[str, str], timeout: int) -> _FakeResponse:
        sent["url"] = url
        sent["json"] = json
        sent["headers"] = headers
        sent["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(requests, "post", _fake_post)

    client = ai_client_api.OpenRouterClient(api_key="test-key", model="openai/gpt-4o-mini", site_url="https://example.com", app_name="td")
    result = client.complete(messages=[{"role": "user", "content": "hello"}], tools=[{"type": "function"}])

    assert result["id"] == "resp-123"
    assert sent["url"] == _FakeBaseOpenRouterClient.BASE_URL
    assert sent["json"]["tool_choice"] == "auto"
    assert "tools" in sent["json"]
    assert sent["headers"]["HTTP-Referer"] == "https://example.com"
    assert sent["headers"]["X-Title"] == "td"


def test_complete_wraps_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP errors should include status code and body in OpenRouterError."""
    monkeypatch.setattr(ai_client_api, "BaseOpenRouterClient", _FakeBaseOpenRouterClient)

    class _FakeResponse:
        status_code = 502
        text = "gateway failed"

        def raise_for_status(self) -> None:
            error = requests.HTTPError("boom")
            error.response = SimpleNamespace(status_code=self.status_code, text=self.text)
            raise error

    def _fake_post(url: str, json: dict[str, Any], headers: dict[str, str], timeout: int) -> _FakeResponse:
        del url, json, headers, timeout
        return _FakeResponse()

    monkeypatch.setattr(requests, "post", _fake_post)
    client = ai_client_api.OpenRouterClient(api_key="test-key")

    with pytest.raises(ai_client_api.OpenRouterError, match="OpenRouter API error 502: gateway failed"):
        client.complete(messages=[{"role": "user", "content": "ping"}])


def test_complete_rejects_non_dict_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete() should reject malformed non-object JSON responses."""
    monkeypatch.setattr(ai_client_api, "BaseOpenRouterClient", _FakeBaseOpenRouterClient)

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> list[str]:
            return ["not", "a", "dict"]

    def _fake_post(url: str, json: dict[str, Any], headers: dict[str, str], timeout: int) -> _FakeResponse:
        del url, json, headers, timeout
        return _FakeResponse()

    monkeypatch.setattr(requests, "post", _fake_post)
    client = ai_client_api.OpenRouterClient(api_key="test-key")

    with pytest.raises(ai_client_api.OpenRouterError, match="invalid response payload"):
        client.complete(messages=[{"role": "user", "content": "ping"}])


def test_get_openrouter_client_validates_env_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dependency helper should read model from env and enforce API key presence."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(HTTPException, match="OPENROUTER_API_KEY"):
        ai_client_api.get_openrouter_client()

    class _CapturedClient:
        def __init__(self, api_key: str | None = None, model: str = ai_client_api.DEFAULT_MODEL, site_url: str = "", app_name: str = "") -> None:
            self.api_key = api_key
            self.model = model
            self.site_url = site_url
            self.app_name = app_name

    monkeypatch.setattr(ai_client_api, "OpenRouterClient", _CapturedClient)
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    client = ai_client_api.get_openrouter_client()
    assert isinstance(client, _CapturedClient)
    assert client.api_key is None
    assert client.model == "openai/gpt-4o-mini"
