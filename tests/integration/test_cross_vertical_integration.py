"""Integration tests: DI wiring, AI tool-calling pipeline, and cross-vertical E2E.

These tests verify:
(a) DI wiring across jira_client_impl and jira_service — JiraClient exposes the full
    method surface that jira_service expects (duck-typed contract) and FastAPI dependency
    injection resolves the correct concrete implementations at request time
(b) The AI tool-calling pipeline using pre-recorded (canned) provider responses —
    no real network calls are made
(c) The cross-vertical integration end-to-end: AI tool call → Jira action →
    Team 9 chat notification, with at least one test demonstrating an AI tool
    call invoking the cross-vertical application
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from jira_service.ai_client_api import get_openrouter_client
from jira_service.main import app, get_jira_client, get_optional_jira_client

pytestmark = pytest.mark.integration

_FAKE_TOKEN = "integration-test-bearer-token"
_AUTH_HEADER = {"Authorization": f"Bearer {_FAKE_TOKEN}"}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_issue(
    issue_id: str = "TD-42",
    title: str = "Integration test issue",
    desc: str = "A description",
    status: str = "to_do",
    members: list[str] | None = None,
    due_date: str | None = None,
) -> MagicMock:
    issue = MagicMock()
    issue.id = issue_id
    issue.title = title
    issue.desc = desc
    issue.status = status
    issue.members = members
    issue.due_date = due_date
    return issue


def _canned_tool_call_response(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    """Pre-recorded OpenRouter response that requests a single tool call."""
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_recorded_abc123",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args),
                            },
                        },
                    ],
                },
            },
        ],
    }


def _canned_text_response(text: str) -> dict[str, Any]:
    """Pre-recorded OpenRouter response with a plain-text final reply."""
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": None,
                },
            },
        ],
    }


# ---------------------------------------------------------------------------
# (a) DI Wiring Across New Components
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestDIWiringNewComponents:
    """Verify DI wiring across ospd-issue-tracker-api, jira_client_impl, and jira_service.

    jira_service treats IssueTrackerClient as Any (duck-typed). These tests confirm
    that the concrete JiraClient satisfies the method contract expected by jira_service
    and that the FastAPI dependency factories resolve correctly at request time.
    """

    def test_jira_client_exposes_all_methods_required_by_jira_service(self) -> None:
        """JiraClient must expose every method that jira_service calls through get_jira_client().

        jira_service relies on duck typing (IssueTrackerClient = Any). This test is
        the DI contract check: if any method is missing, every route that calls it
        will raise AttributeError at request time.
        """
        from jira_client_impl.jira_impl import JiraClient

        for method in ("get_issue", "get_issues", "create_issue", "update_issue", "delete_issue"):
            assert callable(getattr(JiraClient, method, None)), (
                f"JiraClient is missing method required by jira_service: {method}"
            )

    def test_get_client_raises_os_error_when_jira_env_vars_missing(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """jira_client_impl.get_client() must raise OSError when JIRA_* env vars are absent.

        This is the DI factory guard: jira_service calls get_client() to build the
        client injected into each request; missing configuration must fail loudly.
        """
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

        from jira_client_impl import get_client

        with pytest.raises(OSError, match="Missing required environment variables"):
            get_client(interactive=False)

    def test_get_client_returns_jira_client_with_expected_interface(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get_client() must return a JiraClient instance with the full method surface.

        Confirms end-to-end DI wiring: the factory produces an object that jira_service's
        get_jira_client() dependency will inject, and it exposes all expected operations.
        """
        monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
        monkeypatch.setenv("JIRA_USER_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")

        from jira_client_impl import get_client
        from jira_client_impl.jira_impl import JiraClient

        client = get_client(interactive=False)

        assert isinstance(client, JiraClient)
        for method in ("get_issue", "get_issues", "create_issue", "update_issue", "delete_issue"):
            assert callable(getattr(client, method, None))

    def test_get_jira_client_dependency_resolves_in_app(self) -> None:
        """FastAPI get_jira_client dependency must inject the mock client into /issues."""
        mock_client = MagicMock()
        mock_client.get_issues.return_value = iter([_make_mock_issue()])

        app.dependency_overrides[get_jira_client] = lambda: mock_client
        try:
            http_client = TestClient(app, raise_server_exceptions=False)
            response = http_client.get("/issues", headers=_AUTH_HEADER)
        finally:
            app.dependency_overrides.pop(get_jira_client, None)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["issues"], list)
        assert body["issues"][0]["id"] == "TD-42"

    def test_get_openrouter_client_dependency_resolves_in_app(self) -> None:
        """FastAPI get_openrouter_client dependency must inject the mock into /chat."""
        mock_jira = MagicMock()
        mock_openrouter = MagicMock()
        mock_openrouter.complete.return_value = _canned_text_response("Wired correctly.")

        app.dependency_overrides[get_optional_jira_client] = lambda: mock_jira
        app.dependency_overrides[get_openrouter_client] = lambda: mock_openrouter
        try:
            http_client = TestClient(app, raise_server_exceptions=False)
            response = http_client.post("/chat", json={"message": "hello"}, headers=_AUTH_HEADER)
        finally:
            app.dependency_overrides.pop(get_optional_jira_client, None)
            app.dependency_overrides.pop(get_openrouter_client, None)

        assert response.status_code == 200
        assert response.json()["reply"] == "Wired correctly."


# ---------------------------------------------------------------------------
# (b) AI Tool-Calling Pipeline (canned / sandbox provider)
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestAIToolCallingPipeline:
    """Verify the AI tool-calling pipeline using pre-recorded (canned) OpenRouter responses.

    OpenRouterClient.complete() is replaced with a fake whose return values are
    pre-baked JSON matching OpenRouter's real response schema — no live API key
    or network connection required.

    The sequence exercised:
      1. User message arrives at POST /chat
      2. First complete() call returns a tool_call for create_issue
      3. _execute_tool() dispatches to the mock Jira client
      4. Tool result is appended to the message history
      5. Second complete() call returns the final text reply
    """

    @pytest.fixture
    def mock_jira(self) -> MagicMock:
        created = _make_mock_issue(issue_id="TD-99", title="Deploy monitoring alerts")
        client = MagicMock()
        client.create_issue.return_value = created
        client.get_issue.return_value = created
        client.get_issues.return_value = iter([])
        return client

    @pytest.fixture
    def api_client(self, mock_jira: MagicMock) -> Generator[TestClient, None, None]:
        mock_openrouter = MagicMock()
        # Recorded two-step sequence: tool call then final reply
        mock_openrouter.complete.side_effect = [
            _canned_tool_call_response("create_issue", {"title": "Deploy monitoring alerts"}),
            _canned_text_response("Done — I created issue TD-99: Deploy monitoring alerts."),
        ]

        app.dependency_overrides[get_optional_jira_client] = lambda: mock_jira
        app.dependency_overrides[get_openrouter_client] = lambda: mock_openrouter
        client = TestClient(app, raise_server_exceptions=False)
        yield client
        app.dependency_overrides.pop(get_optional_jira_client, None)
        app.dependency_overrides.pop(get_openrouter_client, None)

    def test_tool_call_invokes_create_issue_on_jira_client(
        self, api_client: TestClient, mock_jira: MagicMock,
    ) -> None:
        """AI tool call must invoke create_issue on the Jira client with the correct title."""
        response = api_client.post(
            "/chat",
            json={"message": "@jira Create an issue titled 'Deploy monitoring alerts'"},
            headers=_AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_jira.create_issue.assert_called_once()
        assert mock_jira.create_issue.call_args.kwargs.get("title") == "Deploy monitoring alerts"

    def test_pipeline_records_tool_call_in_actions_list(self, api_client: TestClient) -> None:
        """Response must include an actions list with the dispatched tool call and its result."""
        response = api_client.post(
            "/chat",
            json={"message": "@jira Create an issue titled 'Deploy monitoring alerts'"},
            headers=_AUTH_HEADER,
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["actions"]) == 1
        action = body["actions"][0]
        assert action["tool"] == "create_issue"
        assert action["result"]["id"] == "TD-99"
        assert action["result"]["title"] == "Deploy monitoring alerts"

    def test_pipeline_returns_final_ai_reply_after_tool_execution(self, api_client: TestClient) -> None:
        """Response must include the AI's final text reply produced after tool execution."""
        response = api_client.post(
            "/chat",
            json={"message": "@jira Create an issue titled 'Deploy monitoring alerts'"},
            headers=_AUTH_HEADER,
        )

        assert response.status_code == 200
        assert "TD-99" in response.json()["reply"]

    def test_openrouter_called_twice_for_tool_call_cycle(
        self, api_client: TestClient, mock_jira: MagicMock,
    ) -> None:
        """complete() must be called exactly twice: once to get the tool call, once for the reply."""
        app.dependency_overrides[get_optional_jira_client] = lambda: mock_jira
        mock_openrouter = MagicMock()
        mock_openrouter.complete.side_effect = [
            _canned_tool_call_response("create_issue", {"title": "Deploy monitoring alerts"}),
            _canned_text_response("Created TD-99."),
        ]
        app.dependency_overrides[get_openrouter_client] = lambda: mock_openrouter
        try:
            response = api_client.post(
                "/chat",
                json={"message": "@jira Create an issue titled 'Deploy monitoring alerts'"},
                headers=_AUTH_HEADER,
            )
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)
            app.dependency_overrides.pop(get_optional_jira_client, None)

        assert response.status_code == 200
        assert mock_openrouter.complete.call_count == 2


# ---------------------------------------------------------------------------
# (c) Cross-Vertical Integration End-to-End
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestCrossVerticalIntegrationE2E:
    """Verify the end-to-end cross-vertical flow via POST /chat-relay.

    /chat-relay is the cross-vertical seam:
      1. Receives a user message
      2. Runs the AI tool-calling pipeline (same as /chat)
      3. Posts the reply to Team 9's chat service via _notify_chat_service

    All external I/O (OpenRouter, Jira, Team 9 chat service) is replaced
    with in-process fakes — no real network calls are made.

    At least one test here demonstrates an AI tool call (create_issue) invoking
    the cross-vertical application (Team 9 chat notification).
    """

    _RELAY_TOKEN = "relay-integration-test-token"
    _CHAT_SESSION = "sess-integration-relay"
    _CHANNEL_ID = "C-INTEGRATION-CHANNEL"

    @pytest.fixture(autouse=True)
    def seed_session(self) -> Generator[None, None, None]:
        """Seed an in-memory session so /chat-relay can find the token without OAuth."""
        from jira_service.auth import user_sessions

        user_sessions["relay-integration-user"] = {
            "access_token": self._RELAY_TOKEN,
            "refresh_token": None,
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "cloud_id": "",
            "chat_session_id": self._CHAT_SESSION,
            "channel_id": self._CHANNEL_ID,
        }
        yield
        user_sessions.pop("relay-integration-user", None)

    @pytest.fixture
    def mock_jira(self) -> MagicMock:
        created = _make_mock_issue(issue_id="TD-77", title="Add error alerting to pipeline")
        client = MagicMock()
        client.create_issue.return_value = created
        client.get_issue.return_value = created
        client.get_issues.return_value = iter([])
        return client

    @pytest.fixture
    def relay_client(self, mock_jira: MagicMock) -> Generator[TestClient, None, None]:
        mock_openrouter = MagicMock()
        mock_openrouter.complete.side_effect = [
            _canned_tool_call_response("create_issue", {"title": "Add error alerting to pipeline"}),
            _canned_text_response("Done — created TD-77: Add error alerting to pipeline."),
        ]
        app.dependency_overrides[get_jira_client] = lambda: mock_jira
        app.dependency_overrides[get_openrouter_client] = lambda: mock_openrouter
        client = TestClient(app, raise_server_exceptions=False)
        yield client
        app.dependency_overrides.pop(get_jira_client, None)
        app.dependency_overrides.pop(get_openrouter_client, None)

    def test_ai_tool_call_creates_jira_issue_via_relay(
        self, relay_client: TestClient, mock_jira: MagicMock,
    ) -> None:
        """AI tool call over /chat-relay must invoke create_issue on the Jira client.

        This is the primary cross-vertical test: an AI tool call triggers a Jira
        action that is then relayed to Team 9's chat service.
        """
        with patch("jira_service.main._notify_chat_service", return_value=True):
            response = relay_client.post(
                "/chat-relay",
                json={"message": "@jira Add error alerting to pipeline"},
                headers={"Authorization": f"Bearer {self._RELAY_TOKEN}"},
            )

        assert response.status_code == 200
        mock_jira.create_issue.assert_called_once()
        assert mock_jira.create_issue.call_args.kwargs.get("title") == "Add error alerting to pipeline"

    def test_reply_is_posted_to_team9_chat_channel(self, relay_client: TestClient) -> None:
        """After the AI tool call, the reply must be posted to Team 9's chat channel.

        Demonstrates an AI tool call invoking the cross-vertical application:
        the result of the Jira create_issue action is delivered to Team 9's service.
        """
        posted_calls: list[tuple[str, str, str]] = []

        def _capture_notify(channel_id: str, text: str, session_id: str) -> bool:
            posted_calls.append((channel_id, text, session_id))
            return True

        with patch("jira_service.main._notify_chat_service", side_effect=_capture_notify):
            response = relay_client.post(
                "/chat-relay",
                json={"message": "@jira Add error alerting to pipeline"},
                headers={"Authorization": f"Bearer {self._RELAY_TOKEN}"},
            )

        assert response.status_code == 200
        # Team 9 notification was sent
        assert len(posted_calls) == 1
        channel, text, session = posted_calls[0]
        assert channel == self._CHANNEL_ID
        assert "TD-77" in text
        assert session == self._CHAT_SESSION

    def test_response_includes_create_issue_action_and_result(self, relay_client: TestClient) -> None:
        """Response body from /chat-relay must include the create_issue action with its result."""
        with patch("jira_service.main._notify_chat_service", return_value=True):
            response = relay_client.post(
                "/chat-relay",
                json={"message": "@jira Add error alerting to pipeline"},
                headers={"Authorization": f"Bearer {self._RELAY_TOKEN}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body["actions"]) == 1
        action = body["actions"][0]
        assert action["tool"] == "create_issue"
        assert action["result"]["id"] == "TD-77"
        assert action["result"]["title"] == "Add error alerting to pipeline"

    def test_relay_uses_session_channel_for_notification(self, relay_client: TestClient) -> None:
        """The notification must be sent to the channel stored in the seeded session."""
        captured: list[str] = []

        def _capture_channel(channel_id: str, text: str, session_id: str) -> bool:
            captured.append(channel_id)
            return True

        with patch("jira_service.main._notify_chat_service", side_effect=_capture_channel):
            relay_client.post(
                "/chat-relay",
                json={"message": "@jira Add error alerting to pipeline"},
                headers={"Authorization": f"Bearer {self._RELAY_TOKEN}"},
            )

        assert captured == [self._CHANNEL_ID]
