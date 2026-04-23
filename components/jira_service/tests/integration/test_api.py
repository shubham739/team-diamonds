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

import pytest
from fastapi.testclient import TestClient

from jira_service.main import app, get_jira_client
from jira_service.ai_client_api import OpenRouterError, get_openrouter_client
from work_mgmt_client_interface.client import IssueNotFoundError
from work_mgmt_client_interface.issue import Status

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
    description: str = "A description",
    status: Status = Status.TODO,
    assignee: str | None = None,
    due_date: str | None = None,
) -> MagicMock:
    """Return a MagicMock that behaves like an Issue."""
    issue = MagicMock()
    issue.id = issue_id
    issue.title = title
    issue.description = description
    issue.status = status
    issue.assignee = assignee
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

    def test_valid_callback_returns_user_info(self, api_client: TestClient) -> None:
        from jira_service.main import auth_states

        auth_states["valid_state"] = "valid_state"

        with (
            patch("jira_service.main.exchange_code_for_token", return_value={"access_token": "tok", "expires_in": 3600}),
            patch("jira_service.main.get_user_info", return_value={"account_id": "uid1", "email": "a@b.com", "name": "Alice"}),
            patch("jira_service.main.store_session"),
        ):
            response = api_client.get("/auth/callback", params={"code": "good_code", "state": "valid_state"})

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "authenticated"
        assert body["user_id"] == "uid1"
        assert body["access_token"] == "tok"


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
            json={"title": "New issue", "description": "Details"},
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
                "description": "D",
                "status": "in_progress",
                "assignee": "bob@example.com",
                "due_date": "2026-12-31",
            },
        )
        call_kwargs = mock_jira_client.create_issue.call_args.kwargs
        assert call_kwargs["title"] == "T"
        assert call_kwargs["status"] == Status.IN_PROGRESS
        assert call_kwargs["assignee"] == "bob@example.com"


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


class TestDocs:
    def test_swagger_ui_available(self, api_client: TestClient) -> None:
        response = api_client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_available(self, api_client: TestClient) -> None:
        response = api_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Jira Service API"
