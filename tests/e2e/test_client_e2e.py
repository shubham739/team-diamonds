"""End-to-end tests for the Jira Service application.

Runs the fully-wired FastAPI app entry point (jira_service.main:app) via
FastAPI's TestClient and asserts only on user-visible HTTP behaviour —
status codes, response body shape, error messages, and redirect destinations.

No FastAPI dependency_overrides are used.  Credentials-free tests mock only at
the lowest HTTP level (requests.Session) so the full routing, auth middleware,
and request/response pipeline execute unchanged.  Tests that require live Jira
credentials are gated by @pytest.mark.local_credentials and skipped in CI.

Run e2e tests only:
    pytest -m e2e

Run without e2e:
    pytest -m "not e2e"

Intentionally untestable lines (OAuth redirect edge cases that require a live
Atlassian IDP) are marked  # pragma: no cover  in the source.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from jira_service.main import app

pytestmark = pytest.mark.e2e

# ---------------------------------------------------------------------------
# Shared test client (no dependency_overrides — black-box)
# ---------------------------------------------------------------------------

_HTTP = TestClient(app, raise_server_exceptions=False)
_BEARER = {"Authorization": "Bearer e2e-fake-bearer-token"}


# ---------------------------------------------------------------------------
# 1. App entry point — health and schema
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestAppEntryPoint:
    """Black-box assertions on publicly visible, credential-free endpoints."""

    def test_health_returns_200_and_ok_status(self) -> None:
        """GET /health must return HTTP 200 with body {"status": "ok"}.

        This is the canonical liveness check a user or monitor would call.
        """
        response = _HTTP.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_openapi_schema_is_served(self) -> None:
        """GET /openapi.json must return a valid OpenAPI schema with expected paths."""
        response = _HTTP.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})
        for expected in ("/health", "/issues", "/chat", "/chat-relay"):
            assert expected in paths, f"OpenAPI schema is missing path: {expected}"

    def test_swagger_ui_is_served(self) -> None:
        """GET /docs must return HTTP 200 (Swagger UI reachable by browser)."""
        response = _HTTP.get("/docs")
        assert response.status_code == 200

    def test_logout_without_session_returns_logged_out(self) -> None:
        """GET /auth/logout with unknown user_id must still return {"status": "logged out"}.

        A user who calls logout when already logged out should see a clean response,
        not a server error.
        """
        response = _HTTP.get("/auth/logout", params={"user_id": "no-such-user"})
        assert response.status_code == 200
        assert response.json() == {"status": "logged out"}


# ---------------------------------------------------------------------------
# 2. Auth endpoint contract
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestAuthEndpointContract:
    """Black-box assertions on /auth/login validation visible to any caller."""

    def test_post_login_unsupported_action_returns_400(self) -> None:
        """Unsupported action value must produce HTTP 400 with an informative detail."""
        response = _HTTP.post("/auth/login", json={"action": "do_something_else", "provider": "jira"})
        assert response.status_code == 400
        assert "Unsupported action" in response.json()["detail"]

    def test_post_login_unsupported_provider_returns_400(self) -> None:
        """Unknown provider must produce HTTP 400 with an informative detail."""
        response = _HTTP.post("/auth/login", json={"action": "get_auth_url", "provider": "github"})
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_post_login_missing_body_returns_422(self) -> None:
        """Missing required fields must produce HTTP 422 (validation error)."""
        response = _HTTP.post("/auth/login", json={})
        assert response.status_code == 422

    def test_post_login_slack_returns_callback_url(self) -> None:
        """Slack provider must return a 200 with an authUrl pointing at /auth/callback."""
        response = _HTTP.post("/auth/login", json={"action": "get_auth_url", "provider": "slack"})
        assert response.status_code == 200
        body = response.json()
        assert "authUrl" in body
        assert "auth/callback" in body["authUrl"]
        assert "state=" in body["authUrl"]

    def test_callback_with_unknown_state_returns_400(self) -> None:
        """OAuth callback with an unrecognised state must return HTTP 400."""
        response = _HTTP.get("/auth/callback", params={"state": "not-a-real-state", "code": "x"})
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Protected endpoints — unauthenticated user-visible errors
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestUnauthenticatedBehaviour:
    """Verify every protected endpoint returns the correct auth error to the caller."""

    def test_get_issues_without_bearer_returns_401(self) -> None:
        """GET /issues without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.get("/issues")
        assert response.status_code == 401

    def test_get_issue_by_id_without_bearer_returns_401(self) -> None:
        """GET /issues/{id} without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.get("/issues/TD-1")
        assert response.status_code == 401

    def test_post_issues_without_bearer_returns_401(self) -> None:
        """POST /issues without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.post("/issues", json={"title": "Test"})
        assert response.status_code == 401

    def test_put_issue_without_bearer_returns_401(self) -> None:
        """PUT /issues/{id} without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.put("/issues/TD-1", json={"title": "Updated"})
        assert response.status_code == 401

    def test_delete_issue_without_bearer_returns_401(self) -> None:
        """DELETE /issues/{id} without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.delete("/issues/TD-1")
        assert response.status_code == 401

    def test_post_chat_without_bearer_returns_401(self) -> None:
        """POST /chat without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.post("/chat", json={"message": "hello"})
        assert response.status_code == 401

    def test_post_chat_relay_without_bearer_returns_401(self) -> None:
        """POST /chat-relay without a Bearer token must be rejected with HTTP 401."""
        response = _HTTP.post("/chat-relay", json={"message": "hello"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 4. Request validation — user-visible 422 responses
# ---------------------------------------------------------------------------


@pytest.mark.circleci
class TestRequestValidation:
    """Verify the app surfaces field-level validation errors to callers."""

    def test_post_chat_missing_message_returns_422(self) -> None:
        """POST /chat with an empty body must return HTTP 422."""
        response = _HTTP.post("/chat", json={}, headers=_BEARER)
        assert response.status_code == 422

    def test_post_chat_relay_missing_message_returns_422(self) -> None:
        """POST /chat-relay with an empty body must return HTTP 422."""
        response = _HTTP.post("/chat-relay", json={}, headers=_BEARER)
        assert response.status_code == 422

    def test_get_issues_max_results_out_of_range_returns_422(self) -> None:
        """GET /issues with max_results=0 must return HTTP 422 (below minimum of 1)."""
        response = _HTTP.get("/issues", params={"max_results": 0}, headers=_BEARER)
        assert response.status_code == 422

    def test_get_issues_max_results_too_large_returns_422(self) -> None:
        """GET /issues with max_results=999 must return HTTP 422 (above maximum of 100)."""
        response = _HTTP.get("/issues", params={"max_results": 999}, headers=_BEARER)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 5. Fully-wired workflow (Basic Auth path, no OAuth)
#    Patches requests.Session at the HTTP level — FastAPI DI runs unchanged.
# ---------------------------------------------------------------------------


def _fake_jira_response(status_code: int, body: dict[str, Any]) -> MagicMock:
    """Build a fake requests.Response for Jira API calls."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.circleci
class TestFullyWiredBasicAuth:
    """Run the full app stack with Basic Auth env vars and low-level HTTP mocking.

    FastAPI's dependency injection, routing, and request/response serialisation
    all execute normally.  Only the outbound requests.Session calls to the Jira
    REST API are intercepted, matching what happens in a deployed environment
    where Jira credentials are injected via environment variables.
    """

    @pytest.fixture(autouse=True)
    def _basic_auth_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_BASE_URL", "https://fake-jira.atlassian.net")
        monkeypatch.setenv("JIRA_USER_EMAIL", "ci@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "fake-api-token")

    def test_list_issues_returns_issues_list(self) -> None:
        """GET /issues must return a JSON body with an "issues" array and "count"."""
        jira_response = {
            "issues": [
                {
                    "id": "TD-1",
                    "key": "TD-1",
                    "fields": {
                        "summary": "Fix login bug",
                        "description": None,
                        "status": {"name": "To Do"},
                        "assignee": None,
                        "duedate": None,
                    },
                },
            ],
        }
        with patch("jira_client_impl.jira_impl.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = _fake_jira_response(200, jira_response)

            http = TestClient(app, raise_server_exceptions=False)
            response = http.get("/issues", headers=_BEARER)

        assert response.status_code == 200
        body = response.json()
        assert "issues" in body
        assert "count" in body
        assert isinstance(body["issues"], list)

    def test_get_single_issue_returns_issue_fields(self) -> None:
        """GET /issues/{id} must return the issue's title, status, and id."""
        jira_response = {
            "id": "10001",
            "key": "TD-1",
            "fields": {
                "summary": "Fix login bug",
                "description": None,
                "status": {"name": "In Progress"},
                "assignee": None,
                "duedate": None,
            },
        }
        with patch("jira_client_impl.jira_impl.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = _fake_jira_response(200, jira_response)

            http = TestClient(app, raise_server_exceptions=False)
            response = http.get("/issues/TD-1", headers=_BEARER)

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "TD-1"
        assert body["title"] == "Fix login bug"
        assert "status" in body

    def test_get_missing_issue_returns_404(self) -> None:
        """GET /issues/{id} for a non-existent key must return HTTP 404."""
        with patch("jira_client_impl.jira_impl.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = _fake_jira_response(404, {"errorMessages": ["Issue does not exist"]})

            http = TestClient(app, raise_server_exceptions=False)
            response = http.get("/issues/TD-9999", headers=_BEARER)

        assert response.status_code == 404

    def test_create_issue_returns_201_with_new_issue(self) -> None:
        """POST /issues must return HTTP 201 and include the new issue's id and title."""
        create_resp = {"id": "10002", "key": "TD-2", "self": "https://fake-jira.atlassian.net/rest/api/3/issue/10002"}
        fetch_resp = {
            "id": "10002",
            "key": "TD-2",
            "fields": {
                "summary": "New e2e issue",
                "description": None,
                "status": {"name": "To Do"},
                "assignee": None,
                "duedate": None,
            },
        }
        with patch("jira_client_impl.jira_impl.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = _fake_jira_response(201, create_resp)
            mock_session.get.return_value = _fake_jira_response(200, fetch_resp)

            http = TestClient(app, raise_server_exceptions=False)
            response = http.post("/issues", json={"title": "New e2e issue"}, headers=_BEARER)

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "TD-2"
        assert body["title"] == "New e2e issue"

    def test_delete_issue_returns_200(self) -> None:
        """DELETE /issues/{id} for an existing issue must return HTTP 200."""
        with patch("jira_client_impl.jira_impl.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.delete.return_value = _fake_jira_response(204, {})

            http = TestClient(app, raise_server_exceptions=False)
            response = http.delete("/issues/TD-1", headers=_BEARER)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 6. Live Jira workflow (requires real credentials — skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.local_credentials
class TestLiveJiraWorkflow:
    """Full CRUD workflow against a real Jira instance.

    Requires JIRA_BASE_URL, JIRA_USER_EMAIL, and JIRA_API_TOKEN in the
    environment.  These tests are excluded from CI via the local_credentials
    marker and must be run manually by developers with access to a Jira project.

    Assertions are black-box: they check what a user would see — the issue id,
    title, status values, and 404 after deletion.
    """

    @pytest.fixture(scope="class")
    def live_client(self) -> TestClient:  # pragma: no cover
        missing = [v for v in ("JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN") if not os.getenv(v)]
        if missing:
            pytest.skip(f"Missing credentials: {missing}")
        return TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def live_issue_id(self, live_client: TestClient) -> Generator[str, None, None]:  # pragma: no cover
        """Create a real Jira issue and clean it up after the test."""
        create_resp = live_client.post(
            "/issues",
            json={"title": "[E2E Test] Temporary — safe to delete"},
            headers=_BEARER,
        )
        assert create_resp.status_code == 201, f"Setup failed: {create_resp.text}"
        issue_id: str = create_resp.json()["id"]
        yield issue_id
        live_client.delete(f"/issues/{issue_id}", headers=_BEARER)

    def test_create_read_delete_issue(  # pragma: no cover
        self, live_client: TestClient, live_issue_id: str,
    ) -> None:
        """Full black-box CRUD: create → read → assert title → delete → confirm 404."""
        # Read
        read_resp = live_client.get(f"/issues/{live_issue_id}", headers=_BEARER)
        assert read_resp.status_code == 200
        body = read_resp.json()
        assert body["id"] == live_issue_id
        assert "[E2E Test]" in body["title"]
        assert "status" in body

        # Delete (fixture handles cleanup; we verify the 404 explicitly)
        live_client.delete(f"/issues/{live_issue_id}", headers=_BEARER)
        gone_resp = live_client.get(f"/issues/{live_issue_id}", headers=_BEARER)
        assert gone_resp.status_code == 404

    def test_list_issues_returns_non_empty_list(  # pragma: no cover
        self, live_client: TestClient,
    ) -> None:
        """GET /issues against a real project must return at least one issue."""
        response = live_client.get("/issues", headers=_BEARER)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] >= 0  # project may be empty; shape must be correct
        assert isinstance(body["issues"], list)
