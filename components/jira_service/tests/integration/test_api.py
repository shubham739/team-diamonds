"""Integration tests for the Jira Service FastAPI endpoints.

These tests use FastAPI's TestClient (backed by httpx) so no live server is
needed — they run entirely in-process and are safe to execute in any CI
environment.

All Jira API calls are mocked at the IssueTrackerClient level so the tests
focus on the HTTP contract of the service itself (routing, auth enforcement,
request/response shapes, error mapping) rather than on the Jira client logic
(which is covered separately in jira_client_impl/tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from api.issue import Status
from fastapi.testclient import TestClient

from jira_client_impl.jira_impl import IssueNotFoundError
from jira_service.ai_client_api import OpenRouterClient, OpenRouterError, get_openrouter_client
from jira_service.main import app, get_jira_client

if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_TOKEN = "test-bearer-token"
_AUTH_HEADER = {"Authorization": f"Bearer {_FAKE_TOKEN}"}


def _make_mock_issue(
    issue_id: str = "TD-1",
    title: str = "Test issue",
    desc: str = "A description",
    status: Status = Status.TO_DO,
    members: list[str] | None = None,
    due_date: str | None = None,
) -> MagicMock:
    """Return a MagicMock that behaves like an Issue."""
    issue = MagicMock()
    issue.id = issue_id
    issue.title = title
    issue.desc = desc
    issue.status = status
    issue.members = members
    issue.due_date = due_date
    return issue


def _mock_client_dep(mock_client: MagicMock) -> Any:
    """Return a FastAPI dependency override that injects *mock_client*."""

    def _dep() -> MagicMock:
        return mock_client

    return _dep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_jira_client() -> MagicMock:
    """A pre-configured mock IssueTrackerClient."""
    client = MagicMock()
    client.get_issues.return_value = iter([_make_mock_issue()])
    client.get_issue.return_value = _make_mock_issue()
    client.create_issue.return_value = _make_mock_issue(title="New issue")
    client.update_issue.return_value = _make_mock_issue(title="Updated issue")
    client.delete_issue.return_value = None
    return client


@pytest.fixture
def api_client(mock_jira_client: MagicMock) -> Generator[TestClient, None, None]:
    """TestClient with the Jira client dependency overridden."""
    app.dependency_overrides[get_jira_client] = _mock_client_dep(mock_jira_client)
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self, api_client: TestClient) -> None:
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_returns_ok_status(self, api_client: TestClient) -> None:
        response = api_client.get("/health")
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /auth/login
# ---------------------------------------------------------------------------


class TestAuthLogin:
    def test_redirects_to_atlassian(self, api_client: TestClient) -> None:
        with patch("jira_service.main.get_authorize_url", return_value="https://auth.atlassian.com/authorize?test"):
            response = api_client.get("/auth/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "atlassian.com" in response.headers["location"]

    def test_post_unsupported_action_returns_400(self, api_client: TestClient) -> None:
        response = api_client.post("/auth/login", json={"action": "other", "provider": "jira"})
        assert response.status_code == 400
        assert "Unsupported action" in response.json()["detail"]

    def test_post_unsupported_provider_returns_400(self, api_client: TestClient) -> None:
        response = api_client.post("/auth/login", json={"action": "get_auth_url", "provider": "github"})
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_post_jira_returns_atlassian_url(self, api_client: TestClient) -> None:
        with patch("jira_service.main.get_authorize_url", return_value="https://auth.atlassian.com/authorize?foo"):
            response = api_client.post("/auth/login", json={"action": "get_auth_url", "provider": "jira"})
        assert response.status_code == 200
        assert "atlassian.com" in response.json()["authUrl"]

    def test_post_slack_returns_callback_url(self, api_client: TestClient) -> None:
        response = api_client.post("/auth/login", json={"action": "get_auth_url", "provider": "slack"})
        assert response.status_code == 200
        assert "auth/callback" in response.json()["authUrl"]
        assert "state=" in response.json()["authUrl"]


# ---------------------------------------------------------------------------
# /auth/callback
# ---------------------------------------------------------------------------


class TestAuthCallback:
    def test_missing_params_returns_422(self, api_client: TestClient) -> None:
        response = api_client.get("/auth/callback")
        assert response.status_code == 422

    def test_invalid_state_returns_400(self, api_client: TestClient) -> None:
        response = api_client.get("/auth/callback", params={"code": "abc", "state": "bad_state"})
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    def test_valid_callback_redirects_to_frontend(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["valid_state"] = "jira"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid1", "email": "a@b.com", "name": "Alice"}),
            patch("jira_service.main.get_accessible_resources", return_value=[{"id": "cloud-abc"}]),
            patch("jira_service.main.create_chat_session", return_value=("sess-1", "https://chat.example.com/login")),
            patch("jira_service.main._write_session_to_dynamodb"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}),
        ):
            response = api_client.get("/auth/callback", params={"code": "good_code", "state": "valid_state"}, follow_redirects=False)

        assert response.status_code == 307
        location = response.headers["location"]
        assert "/jira/callback" in location
        assert "access_token=tok" in location
        assert "user_id=uid1" in location

    def test_valid_callback_redirects_to_frontend_when_requested(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["valid_state_fe__frontend"] = "jira"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid1", "email": "a@b.com", "name": "Alice"}),
            patch("jira_service.main.get_accessible_resources", return_value=[{"id": "cloud-123"}]),
            patch("jira_service.main.create_chat_session", return_value=("sess-1", "https://chat.example.com/login")),
            patch("jira_service.main._write_session_to_dynamodb"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "FRONTEND_URL": "http://localhost:3000"}),
        ):
            response = api_client.get(
                "/auth/callback",
                params={"code": "good_code", "state": "valid_state_fe__frontend"},
                follow_redirects=False,
            )

        assert response.status_code == 307
        location = response.headers["location"]
        assert "/jira/callback" in location
        assert "access_token=tok" in location
        assert "user_id=uid1" in location

    def test_callback_stores_chat_session_id(self, api_client: TestClient) -> None:
        from jira_service.auth import user_sessions
        from jira_service.main import auth_states

        auth_states["state_ch"] = "jira"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok-ch", "refresh_token": "ref", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid_ch", "email": "x@y.com", "name": "X"}),
            patch("jira_service.main.get_accessible_resources", return_value=[{"id": "cloud-1"}]),
            patch("jira_service.main.create_chat_session", return_value=("sess-ch", "https://chat.example.com/login")),
            patch("jira_service.main._write_session_to_dynamodb"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}),
        ):
            api_client.get("/auth/callback", params={"code": "c", "state": "state_ch"}, follow_redirects=False)

        assert user_sessions["uid_ch"]["chat_session_id"] == "sess-ch"
        assert user_sessions["uid_ch"]["team9_login_url"] == "https://chat.example.com/login"

    def test_callback_stores_cloud_id_from_accessible_resources(self, api_client: TestClient) -> None:
        from jira_service.auth import user_sessions
        from jira_service.main import auth_states

        auth_states["state_cloud"] = "jira"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok", "refresh_token": "ref", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid_cloud", "email": "x@y.com", "name": "X"}),
            patch("jira_service.main.get_accessible_resources", return_value=[{"id": "cloud-xyz"}]),
            patch("jira_service.main.create_chat_session", return_value=("sess-1", "https://chat.example.com/login")),
        ):
            api_client.get("/auth/callback", params={"code": "c", "state": "state_cloud"})

        assert user_sessions["uid_cloud"]["cloud_id"] == "cloud-xyz"

    def test_callback_succeeds_when_accessible_resources_fails(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["state_fail"] = "jira"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok-fail", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid_fail", "email": "f@f.com", "name": "F"}),
            patch("jira_service.main.get_accessible_resources", side_effect=Exception("network error")),
            patch("jira_service.main.create_chat_session", return_value=("sess-1", "https://chat.example.com/login")),
            patch("jira_service.main._write_session_to_dynamodb"),
        ):
            response = api_client.get(
                "/auth/callback",
                params={"code": "c", "state": "state_fail"},
                follow_redirects=False,
            )

        assert response.status_code == 307

    def test_slack_callback_redirects_to_team9_login_url(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["slack_state_1"] = "slack"

        with (
            patch("jira_service.main.create_chat_session", return_value=("sess-s1", "https://chat.example.com/login?state=team9abc")),
            patch("jira_service.main.store_session"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}),
        ):
            response = api_client.get("/auth/callback", params={"state": "slack_state_1"}, follow_redirects=False)

        assert response.status_code in (302, 307)
        assert "chat.example.com/login" in response.headers["location"]

    def test_slack_callback_registers_team9_state_for_return(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["slack_state_2"] = "slack"

        with (
            patch("jira_service.main.create_chat_session", return_value=("sess-s2", "https://chat.example.com/login?state=TEAM9STATE")),
            patch("jira_service.main.store_session"),
            patch("jira_service.main._write_session_to_dynamodb"),
            patch("jira_service.main._save_auth_state_to_dynamodb"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}),
        ):
            api_client.get("/auth/callback", params={"state": "slack_state_2"}, follow_redirects=False)

        assert auth_states.get("TEAM9STATE", "").startswith("return:")

    def test_slack_callback_redirects_home_when_no_team9_url(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["slack_state_3"] = "slack"

        with (
            patch("jira_service.main.create_chat_session", return_value=("", None)),
            patch("jira_service.main.store_session"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "FRONTEND_URL": "http://localhost:3000"}),
        ):
            response = api_client.get("/auth/callback", params={"state": "slack_state_3"}, follow_redirects=False)

        assert response.status_code in (302, 307)
        assert "localhost:3000" in response.headers["location"]

    def test_slack_callback_handles_chat_session_failure(self, api_client: TestClient) -> None:
        from jira_service.auth import AuthenticationError
        from jira_service.main import auth_states

        auth_states["slack_state_4"] = "slack"

        with (
            patch("jira_service.main.create_chat_session", side_effect=AuthenticationError("chat down")),
            patch("jira_service.main.store_session"),
            patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "FRONTEND_URL": "http://localhost:3000"}),
        ):
            response = api_client.get("/auth/callback", params={"state": "slack_state_4"}, follow_redirects=False)

        assert response.status_code in (302, 307)

    def test_slack_return_callback_redirects_to_frontend(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["team9_return_state"] = "return:http://localhost:3000"

        response = api_client.get(
            "/auth/callback",
            params={"state": "team9_return_state", "code": "slack_code_xyz"},
            follow_redirects=False,
        )

        assert response.status_code in (302, 307)
        assert "localhost:3000" in response.headers["location"]



# ---------------------------------------------------------------------------
# /auth/logout
# ---------------------------------------------------------------------------


class TestAuthLogout:
    def test_logout_without_user_id(self, api_client: TestClient) -> None:
        response = api_client.get("/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"status": "logged out"}

    def test_logout_with_unknown_user_id(self, api_client: TestClient) -> None:
        response = api_client.get("/auth/logout", params={"user_id": "nobody"})
        assert response.status_code == 200

    def test_logout_clears_session(self, api_client: TestClient) -> None:
        from jira_service.auth import user_sessions

        user_sessions["uid-to-logout"] = {"access_token": "tok"}
        response = api_client.get("/auth/logout", params={"user_id": "uid-to-logout"})
        assert response.status_code == 200
        assert "uid-to-logout" not in user_sessions


# ---------------------------------------------------------------------------
# GET / — root (requires auth)
# ---------------------------------------------------------------------------


class TestRoot:
    def test_requires_auth(self) -> None:
        # Use a plain client with NO dependency override so the real oauth2_scheme runs
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 401

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.side_effect = RuntimeError("boom")
        response = api_client.get("/", headers=_AUTH_HEADER)
        assert response.status_code == 500

    def test_returns_issues(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.return_value = iter([_make_mock_issue("TD-1", "Bug")])
        response = api_client.get("/", headers=_AUTH_HEADER)
        assert response.status_code == 200
        body = response.json()
        assert "issues" in body
        assert body["issues"][0]["id"] == "TD-1"


# ---------------------------------------------------------------------------
# GET /issues — list
# ---------------------------------------------------------------------------


class TestListIssues:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/issues")
        assert response.status_code == 401

    def test_returns_issues_list(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.return_value = iter(
            [
                _make_mock_issue("TD-1"),
                _make_mock_issue("TD-2"),
            ],
        )
        response = api_client.get("/issues", headers=_AUTH_HEADER)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert len(body["issues"]) == 2

    def test_passes_filters_to_client(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.return_value = iter([])
        api_client.get("/issues", headers=_AUTH_HEADER, params={"title": "bug", "status": "in_progress"})
        mock_jira_client.get_issues.assert_called_once()
        call_kwargs = mock_jira_client.get_issues.call_args.kwargs
        assert call_kwargs["title"] == "bug"
        assert call_kwargs["status"] == Status.IN_PROGRESS

    def test_invalid_max_results_returns_422(self, api_client: TestClient) -> None:
        response = api_client.get("/issues", headers=_AUTH_HEADER, params={"max_results": 0})
        assert response.status_code == 422

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.side_effect = RuntimeError("boom")
        response = api_client.get("/issues", headers=_AUTH_HEADER)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /issues/{issue_id}
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/issues/TD-1")
        assert response.status_code == 401

    def test_returns_issue(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issue.return_value = _make_mock_issue("TD-1", "My bug")
        response = api_client.get("/issues/TD-1", headers=_AUTH_HEADER)
        assert response.status_code == 200
        assert response.json()["id"] == "TD-1"
        assert response.json()["title"] == "My bug"

    def test_not_found_returns_404(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issue.side_effect = IssueNotFoundError("not found")
        response = api_client.get("/issues/TD-999", headers=_AUTH_HEADER)
        assert response.status_code == 404
        assert "TD-999" in response.json()["detail"]

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issue.side_effect = RuntimeError("boom")
        response = api_client.get("/issues/TD-1", headers=_AUTH_HEADER)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /issues
# ---------------------------------------------------------------------------


class TestCreateIssue:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/issues", json={"title": "x"})
        assert response.status_code == 401

    def test_creates_issue(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_issue.return_value = _make_mock_issue("TD-10", "New issue")
        response = api_client.post(
            "/issues",
            headers=_AUTH_HEADER,
            json={"title": "New issue", "desc": "Details"},
        )
        assert response.status_code == 201
        assert response.json()["id"] == "TD-10"

    def test_passes_all_fields_to_client(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_issue.return_value = _make_mock_issue()
        api_client.post(
            "/issues",
            headers=_AUTH_HEADER,
            json={
                "title": "T",
                "desc": "D",
                "status": "in_progress",
                "members": ["bob@example.com"],
                "due_date": "2026-12-31",
                "board_id": "BOARD-1",
            },
        )
        call_kwargs = mock_jira_client.create_issue.call_args.kwargs
        assert call_kwargs["title"] == "T"
        assert call_kwargs["status"] == Status.IN_PROGRESS
        assert call_kwargs["members"] == ["bob@example.com"]
        assert call_kwargs["board_id"] == "BOARD-1"

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_issue.side_effect = RuntimeError("boom")
        response = api_client.post("/issues", headers=_AUTH_HEADER, json={"title": "x"})
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# PUT /issues/{issue_id}
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put("/issues/TD-1", json={"title": "x"})
        assert response.status_code == 401

    def test_updates_issue(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.update_issue.return_value = _make_mock_issue("TD-1", "Updated")
        response = api_client.put(
            "/issues/TD-1",
            headers=_AUTH_HEADER,
            json={"title": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_not_found_returns_404(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.update_issue.side_effect = IssueNotFoundError("not found")
        response = api_client.put("/issues/TD-999", headers=_AUTH_HEADER, json={"title": "x"})
        assert response.status_code == 404

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.update_issue.side_effect = RuntimeError("boom")
        response = api_client.put("/issues/TD-1", headers=_AUTH_HEADER, json={"title": "x"})
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /issues/{issue_id}
# ---------------------------------------------------------------------------


class TestDeleteIssue:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete("/issues/TD-1")
        assert response.status_code == 401

    def test_deletes_issue(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        response = api_client.delete("/issues/TD-1", headers=_AUTH_HEADER)
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        mock_jira_client.delete_issue.assert_called_once_with("TD-1")

    def test_not_found_returns_404(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.delete_issue.side_effect = IssueNotFoundError("not found")
        response = api_client.delete("/issues/TD-999", headers=_AUTH_HEADER)
        assert response.status_code == 404

    def test_returns_500_on_unexpected_error(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.delete_issue.side_effect = RuntimeError("boom")
        response = api_client.delete("/issues/TD-1", headers=_AUTH_HEADER)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Docs endpoints
# ---------------------------------------------------------------------------


class TestChat:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/chat", json={"message": "list issues"})
        assert response.status_code == 401

    def test_missing_message_returns_422(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            response = api_client.post("/chat", headers=_AUTH_HEADER, json={})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_simple_reply_no_tool_calls(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Hello!", "tool_calls": None}}],
        }
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            response = api_client.post("/chat", headers=_AUTH_HEADER, json={"message": "Hi"})
            assert response.status_code == 200
            body = response.json()
            assert body["reply"] == "Hello!"
            assert body["actions"] == []
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_tool_call_list_issues(self, api_client: TestClient, mock_jira_client: MagicMock) -> None:
        mock_jira_client.get_issues.return_value = iter([_make_mock_issue("TD-1", "Bug")])
        mock_or = MagicMock()
        mock_or.complete.side_effect = [
            {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {"id": "c1", "type": "function", "function": {"name": "list_issues", "arguments": "{}"}},
                            ],
                        },
                    },
                ],
            },
            {
                "choices": [
                    {"finish_reason": "stop", "message": {"role": "assistant", "content": "Found 1 issue.", "tool_calls": None}},
                ],
            },
        ]
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            response = api_client.post("/chat", headers=_AUTH_HEADER, json={"message": "List issues"})
            assert response.status_code == 200
            body = response.json()
            assert body["reply"] == "Found 1 issue."
            assert len(body["actions"]) == 1
            assert body["actions"][0]["tool"] == "list_issues"
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_openrouter_error_returns_502(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.side_effect = OpenRouterError("bad key")
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            response = api_client.post("/chat", headers=_AUTH_HEADER, json={"message": "hello"})
            assert response.status_code == 502
            assert "OpenRouter" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_returns_500_on_unexpected_error(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.side_effect = RuntimeError("boom")
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            response = api_client.post("/chat", headers=_AUTH_HEADER, json={"message": "hello"})
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)


# ---------------------------------------------------------------------------
# POST /chat-relay
# ---------------------------------------------------------------------------

_RELAY_BODY = {"message": "What tickets are assigned to me?"}

_FAKE_SESSION = {
    "access_token": _FAKE_TOKEN,
    "chat_session_id": "sess-abc",
    "channel_id": "C123",
}


def _mock_relay_session(session: dict[str, Any] = _FAKE_SESSION) -> Any:
    """Patch get_session_by_token to return a fake session for relay/channel tests."""
    return patch("jira_service.main.get_session_by_token", return_value=("user-1", session))


class TestChatRelay:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/chat-relay", json=_RELAY_BODY)
        assert response.status_code == 401

    def test_missing_message_returns_422(self, api_client: TestClient) -> None:
        app.dependency_overrides[get_openrouter_client] = lambda: MagicMock()
        try:
            with _mock_relay_session():
                response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json={})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_no_session_returns_401(self, api_client: TestClient) -> None:
        app.dependency_overrides[get_openrouter_client] = lambda: MagicMock()
        try:
            with patch("jira_service.main.get_session_by_token", return_value=None):
                response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)
            assert response.status_code == 401
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_no_channel_returns_400(self, api_client: TestClient) -> None:
        app.dependency_overrides[get_openrouter_client] = lambda: MagicMock()
        try:
            session = {**_FAKE_SESSION, "channel_id": ""}
            with _mock_relay_session(session):
                with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "TEAM9_CHANNEL_ID": ""}):
                    with patch("jira_service.main.httpx.Client") as mock_cls:
                        mock_http = MagicMock()
                        mock_http.__enter__ = MagicMock(return_value=mock_http)
                        mock_http.__exit__ = MagicMock(return_value=False)
                        mock_http.get.side_effect = Exception("connection failed")
                        mock_cls.return_value = mock_http
                        response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)
            assert response.status_code == 400
            assert "No channel available" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_no_chat_session_returns_400(self, api_client: TestClient) -> None:
        app.dependency_overrides[get_openrouter_client] = lambda: MagicMock()
        try:
            session = {**_FAKE_SESSION, "chat_session_id": ""}
            with _mock_relay_session(session):
                response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)
            assert response.status_code == 400
            assert "Team 9 session" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_returns_reply_and_calls_chat_service(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "You have 2 tickets.", "tool_calls": None}}],
        }
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            with _mock_relay_session():
                with patch("jira_service.main._notify_chat_service") as mock_notify:
                    response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)

            assert response.status_code == 200
            body = response.json()
            assert body["reply"] == "You have 2 tickets."
            assert body["actions"] == []
            mock_notify.assert_called_once_with("C123", "You have 2 tickets.", "sess-abc")
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_openrouter_error_returns_502(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.side_effect = OpenRouterError("bad key")
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            with _mock_relay_session():
                with patch("jira_service.main._notify_chat_service"):
                    response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)
            assert response.status_code == 502
            assert "OpenRouter" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_unexpected_error_returns_500(self, api_client: TestClient) -> None:
        mock_or = MagicMock()
        mock_or.complete.side_effect = RuntimeError("boom")
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        try:
            with _mock_relay_session():
                with patch("jira_service.main._notify_chat_service"):
                    response = api_client.post("/chat-relay", headers=_AUTH_HEADER, json=_RELAY_BODY)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)


class TestChatChannels:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/auth/channels").status_code == 401

    def test_no_session_returns_401(self, api_client: TestClient) -> None:
        with patch("jira_service.main.get_session_by_token", return_value=None):
            response = api_client.get("/auth/channels", headers=_AUTH_HEADER)
        assert response.status_code == 401

    def test_no_chat_session_returns_400(self, api_client: TestClient) -> None:
        session = {**_FAKE_SESSION, "chat_session_id": ""}
        with _mock_relay_session(session):
            response = api_client.get("/auth/channels", headers=_AUTH_HEADER)
        assert response.status_code == 400

    def test_returns_channels_from_chat_service(self, api_client: TestClient) -> None:
        channels_payload = {"channels": [{"id": "C1", "name": "general"}]}
        mock_response = MagicMock()
        mock_response.json.return_value = channels_payload
        mock_response.raise_for_status = MagicMock()

        with _mock_relay_session():
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
                with patch("jira_service.main.httpx.Client") as mock_client_cls:
                    mock_http = MagicMock()
                    mock_http.__enter__ = MagicMock(return_value=mock_http)
                    mock_http.__exit__ = MagicMock(return_value=False)
                    mock_http.get.return_value = mock_response
                    mock_client_cls.return_value = mock_http
                    response = api_client.get("/auth/channels", headers=_AUTH_HEADER)

        assert response.status_code == 200
        assert response.json() == channels_payload

    def test_chat_service_error_returns_502(self, api_client: TestClient) -> None:
        with _mock_relay_session():
            with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
                with patch("jira_service.main.httpx.Client") as mock_client_cls:
                    mock_http = MagicMock()
                    mock_http.__enter__ = MagicMock(return_value=mock_http)
                    mock_http.__exit__ = MagicMock(return_value=False)
                    mock_http.get.side_effect = httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock())
                    mock_client_cls.return_value = mock_http
                    response = api_client.get("/auth/channels", headers=_AUTH_HEADER)

        assert response.status_code == 502


class TestSelectChannel:
    def test_requires_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.post("/auth/select-channel", json={"channel_id": "C1"}).status_code == 401

    def test_no_session_returns_401(self, api_client: TestClient) -> None:
        with patch("jira_service.main.get_session_by_token", return_value=None):
            response = api_client.post("/auth/select-channel", headers=_AUTH_HEADER, json={"channel_id": "C1"})
        assert response.status_code == 401

    def test_stores_channel_and_returns_ok(self, api_client: TestClient) -> None:
        with _mock_relay_session():
            with patch("jira_service.main.update_session_channel") as mock_update:
                response = api_client.post("/auth/select-channel", headers=_AUTH_HEADER, json={"channel_id": "C42"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "channel_id": "C42"}
        mock_update.assert_called_once_with("user-1", "C42")

    def test_missing_channel_id_returns_422(self, api_client: TestClient) -> None:
        with _mock_relay_session():
            response = api_client.post("/auth/select-channel", headers=_AUTH_HEADER, json={})
        assert response.status_code == 422


class TestOpenRouterClient:
    def test_init_and_close(self) -> None:
        client = OpenRouterClient("test-key")
        client.close()

    def test_context_manager(self) -> None:
        with OpenRouterClient("test-key"):
            pass


class TestDocs:
    def test_swagger_ui_available(self, api_client: TestClient) -> None:
        response = api_client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_available(self, api_client: TestClient) -> None:
        response = api_client.get("/prod/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Jira Service API"
