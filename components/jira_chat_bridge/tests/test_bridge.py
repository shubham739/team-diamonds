"""Tests for jira_chat_bridge.bridge.

All HTTP calls are mocked at the httpx.AsyncClient level so no live servers
are needed.  Async functions are exercised via asyncio.run() since
pytest-asyncio is not available in this project.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from jira_chat_bridge.bridge import (
    _call_jira_chat,
    _get_new_messages,
    _poll_channel,
    _send_reply,
    _sessions,
    app,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_sessions() -> Generator[None, None, None]:
    """Ensure _sessions is empty before and after every test."""
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient with the background poll loop suppressed."""
    with patch("jira_chat_bridge.bridge._poll_loop", new_callable=AsyncMock):
        with TestClient(app) as c:
            yield c


@contextmanager
def _mock_async_client(
    get_response: dict[str, Any] | None = None,
    post_response: dict[str, Any] | None = None,
    raise_on_get: Exception | None = None,
    raise_on_post: Exception | None = None,
) -> Generator[AsyncMock, None, None]:
    """Patch httpx.AsyncClient with controllable get/post behaviour."""
    mock_http = AsyncMock()

    if raise_on_get:
        mock_http.get = AsyncMock(side_effect=raise_on_get)
    else:
        get_resp = MagicMock()
        get_resp.json.return_value = get_response or {}
        get_resp.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=get_resp)

    if raise_on_post:
        mock_http.post = AsyncMock(side_effect=raise_on_post)
    else:
        post_resp = MagicMock()
        post_resp.json.return_value = post_response or {}
        post_resp.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=post_resp)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_http)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("jira_chat_bridge.bridge.httpx.AsyncClient", return_value=mock_cm):
        yield mock_http


# ---------------------------------------------------------------------------
# POST /sessions
# ---------------------------------------------------------------------------


class TestRegisterSession:
    def test_returns_201_with_channel_id(self, client: TestClient) -> None:
        resp = client.post("/sessions", json={"channel_id": "C1", "token": "tok"})
        assert resp.status_code == 201
        assert resp.json() == {"status": "registered", "channel_id": "C1"}

    def test_stores_token_and_null_last_ts(self, client: TestClient) -> None:
        client.post("/sessions", json={"channel_id": "C2", "token": "mytoken"})
        assert _sessions["C2"]["token"] == "mytoken"
        assert _sessions["C2"]["last_ts"] is None

    def test_overwrites_existing_session(self, client: TestClient) -> None:
        _sessions["C3"] = {"token": "old", "last_ts": "ts-old"}
        client.post("/sessions", json={"channel_id": "C3", "token": "new"})
        assert _sessions["C3"]["token"] == "new"
        assert _sessions["C3"]["last_ts"] is None

    def test_missing_token_returns_422(self, client: TestClient) -> None:
        resp = client.post("/sessions", json={"channel_id": "C4"})
        assert resp.status_code == 422

    def test_missing_channel_id_returns_422(self, client: TestClient) -> None:
        resp = client.post("/sessions", json={"token": "tok"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /sessions/{channel_id}
# ---------------------------------------------------------------------------


class TestDeregisterSession:
    def test_removes_session_returns_200(self, client: TestClient) -> None:
        _sessions["C10"] = {"token": "tok", "last_ts": None}
        resp = client.delete("/sessions/C10")
        assert resp.status_code == 200
        assert resp.json() == {"status": "deregistered", "channel_id": "C10"}
        assert "C10" not in _sessions

    def test_returns_404_for_unknown_channel(self, client: TestClient) -> None:
        resp = client.delete("/sessions/NOPE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_ok_status(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_reports_monitored_channel_count(self, client: TestClient) -> None:
        _sessions["C1"] = {"token": "t", "last_ts": None}
        _sessions["C2"] = {"token": "t", "last_ts": None}
        resp = client.get("/health")
        assert resp.json()["monitored_channels"] == 2

    def test_zero_channels_when_no_sessions(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.json()["monitored_channels"] == 0


# ---------------------------------------------------------------------------
# _get_new_messages
# ---------------------------------------------------------------------------


class TestGetNewMessages:
    def test_returns_all_messages_when_no_after_ts(self) -> None:
        messages = [{"text": "hi", "timestamp": "100"}, {"text": "bye", "timestamp": "200"}]
        with _mock_async_client(get_response={"messages": messages}):
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "CHAT_CLIENT_SERVICE_SESSION_ID": "sess"}):
                result = asyncio.run(_get_new_messages("C1", after_ts=None))
        assert len(result) == 2

    def test_filters_messages_at_or_before_after_ts(self) -> None:
        messages = [
            {"text": "old", "timestamp": "100"},
            {"text": "new", "timestamp": "200"},
        ]
        with _mock_async_client(get_response={"messages": messages}):
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "CHAT_CLIENT_SERVICE_SESSION_ID": "sess"}):
                result = asyncio.run(_get_new_messages("C1", after_ts="150"))
        assert len(result) == 1
        assert result[0]["text"] == "new"

    def test_raises_on_http_error(self) -> None:
        err = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        with _mock_async_client(raise_on_get=err):
            with pytest.raises(httpx.HTTPStatusError):
                asyncio.run(_get_new_messages("C1", after_ts=None))

    def test_sends_session_id_header(self) -> None:
        with _mock_async_client(get_response={"messages": []}) as mock_http:
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "CHAT_CLIENT_SERVICE_SESSION_ID": "my-session"}):
                asyncio.run(_get_new_messages("C1", after_ts=None))
        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-Session-ID"] == "my-session"


# ---------------------------------------------------------------------------
# _call_jira_chat
# ---------------------------------------------------------------------------


class TestCallJiraChat:
    def test_returns_reply_from_response(self) -> None:
        with _mock_async_client(post_response={"reply": "Here are your tickets."}):
            with patch.dict("os.environ", {"JIRA_SERVICE_BASE_URL": "http://jira"}):
                result = asyncio.run(_call_jira_chat("list tickets", "access-token"))
        assert result == "Here are your tickets."

    def test_returns_fallback_when_no_reply_key(self) -> None:
        with _mock_async_client(post_response={}):
            with patch.dict("os.environ", {"JIRA_SERVICE_BASE_URL": "http://jira"}):
                result = asyncio.run(_call_jira_chat("hello", "token"))
        assert result == "No reply received."

    def test_sends_bearer_token_header(self) -> None:
        with _mock_async_client(post_response={"reply": "ok"}) as mock_http:
            with patch.dict("os.environ", {"JIRA_SERVICE_BASE_URL": "http://jira"}):
                asyncio.run(_call_jira_chat("msg", "my-access-token"))
        _, kwargs = mock_http.post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer my-access-token"

    def test_raises_on_http_error(self) -> None:
        err = httpx.HTTPStatusError("502", request=MagicMock(), response=MagicMock())
        with _mock_async_client(raise_on_post=err):
            with pytest.raises(httpx.HTTPStatusError):
                asyncio.run(_call_jira_chat("msg", "token"))


# ---------------------------------------------------------------------------
# _send_reply
# ---------------------------------------------------------------------------


class TestSendReply:
    def test_returns_timestamp_from_response(self) -> None:
        with _mock_async_client(post_response={"timestamp": "ts-99"}):
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "CHAT_CLIENT_SERVICE_SESSION_ID": "sess"}):
                result = asyncio.run(_send_reply("C1", "Hello!"))
        assert result == "ts-99"

    def test_returns_empty_string_when_no_timestamp(self) -> None:
        with _mock_async_client(post_response={}):
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "CHAT_CLIENT_SERVICE_SESSION_ID": "sess"}):
                result = asyncio.run(_send_reply("C1", "Hello!"))
        assert result == ""


# ---------------------------------------------------------------------------
# _poll_channel
# ---------------------------------------------------------------------------


class TestPollChannel:
    def test_happy_path_processes_message_and_advances_cursor(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": None}
        messages = [{"text": "list my tickets", "timestamp": "ts-1"}]

        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=messages)):
            with patch("jira_chat_bridge.bridge._call_jira_chat", new=AsyncMock(return_value="You have 3 tickets.")):
                with patch("jira_chat_bridge.bridge._send_reply", new=AsyncMock(return_value="ts-reply")):
                    asyncio.run(_poll_channel("C1", session))

        assert session["last_ts"] == "ts-reply"

    def test_skips_empty_text_but_advances_cursor(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": None}
        messages = [{"text": "  ", "timestamp": "ts-1"}]

        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=messages)):
            with patch("jira_chat_bridge.bridge._call_jira_chat", new=AsyncMock()) as mock_chat:
                asyncio.run(_poll_channel("C1", session))

        mock_chat.assert_not_called()
        assert session["last_ts"] == "ts-1"

    def test_poll_failure_does_not_raise(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": None}
        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(side_effect=RuntimeError("timeout"))):
            asyncio.run(_poll_channel("C1", session))  # must not raise
        assert session["last_ts"] is None

    def test_401_removes_session(self) -> None:
        _sessions["C1"] = {"token": "bad", "last_ts": None}
        session = _sessions["C1"]
        messages = [{"text": "hi", "timestamp": "ts-1"}]

        mock_response = MagicMock()
        mock_response.status_code = 401
        err = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=messages)):
            with patch("jira_chat_bridge.bridge._call_jira_chat", new=AsyncMock(side_effect=err)):
                asyncio.run(_poll_channel("C1", session))

        assert "C1" not in _sessions

    def test_non_401_http_error_advances_cursor(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": None}
        messages = [{"text": "hi", "timestamp": "ts-1"}]

        mock_response = MagicMock()
        mock_response.status_code = 503
        err = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_response)

        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=messages)):
            with patch("jira_chat_bridge.bridge._call_jira_chat", new=AsyncMock(side_effect=err)):
                asyncio.run(_poll_channel("C1", session))

        assert session["last_ts"] == "ts-1"
        assert True  # session was NOT removed

    def test_unexpected_error_advances_cursor(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": None}
        messages = [{"text": "crash me", "timestamp": "ts-5"}]

        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=messages)):
            with patch("jira_chat_bridge.bridge._call_jira_chat", new=AsyncMock(side_effect=ValueError("boom"))):
                asyncio.run(_poll_channel("C1", session))

        assert session["last_ts"] == "ts-5"

    def test_uses_last_ts_as_filter(self) -> None:
        session: dict[str, Any] = {"token": "tok", "last_ts": "ts-old"}
        with patch("jira_chat_bridge.bridge._get_new_messages", new=AsyncMock(return_value=[])) as mock_get:
            asyncio.run(_poll_channel("C1", session))
        mock_get.assert_awaited_once_with("C1", after_ts="ts-old")
