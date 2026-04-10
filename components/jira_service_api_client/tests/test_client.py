"""Unit tests for jira_service_api_client.

All HTTP calls are intercepted with httpx's built-in MockTransport so no
live service is required.  Tests cover:

- IssueData.from_dict — model parsing and edge-cases
- JiraServiceClient — all public methods, success paths and error paths
- Error mapping — 404 → ServiceIssueNotFoundError, other → ServiceClientError
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from jira_service_api_client.client import (
    JiraServiceClient,
    ServiceClientError,
    ServiceIssueNotFoundError,
)
from jira_service_api_client.models import IssueData, Status

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "http://test-service"
_TOKEN = "test-token"


def _issue_payload(
    issue_id: str = "TD-1",
    title: str = "Test issue",
    desc: str = "A description",
    status: str = "todo",
    members: list[str] | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "title": title,
        "desc": desc,
        "status": status,
        "members": members,
        "due_date": due_date,
    }


def _make_response(status_code: int, json_body: Any = None, *, text: str = "") -> httpx.Response:
    """Build a minimal httpx.Response for testing _raise_for_status."""
    if json_body is not None:
        import json

        content = json.dumps(json_body).encode()
        headers = {"content-type": "application/json"}
    else:
        content = text.encode()
        headers = {}
    return httpx.Response(status_code=status_code, content=content, headers=headers)


# ---------------------------------------------------------------------------
# IssueData.from_dict
# ---------------------------------------------------------------------------


class TestIssueDataFromDict:
    def test_all_fields_populated(self) -> None:
        data = _issue_payload(
            issue_id="TD-42",
            title="My bug",
            desc="Details here",
            status="in_progress",
            members=["alice@example.com"],
            due_date="2026-12-31",
        )
        issue = IssueData.from_dict(data)
        assert issue.id == "TD-42"
        assert issue.title == "My bug"
        assert issue.desc == "Details here"
        assert issue.status == Status.IN_PROGRESS
        assert issue.members == ["alice@example.com"]
        assert issue.due_date == "2026-12-31"

    def test_optional_fields_default_none(self) -> None:
        issue = IssueData.from_dict(_issue_payload())
        assert issue.members is None
        assert issue.due_date is None

    def test_all_status_values(self) -> None:
        for raw, expected in [
            ("todo", Status.TO_DO),
            ("to_do", Status.TO_DO),
            ("in_progress", Status.IN_PROGRESS),
            ("complete", Status.COMPLETED),
            ("completed", Status.COMPLETED),
            ("cancelled", Status.COMPLETED),
        ]:
            issue = IssueData.from_dict(_issue_payload(status=raw))
            assert issue.status == expected

    def test_missing_optional_keys_do_not_raise(self) -> None:
        minimal = {"id": "TD-1", "title": "t", "desc": "d", "status": "todo"}
        issue = IssueData.from_dict(minimal)
        assert issue.members is None
        assert issue.due_date is None

    def test_legacy_keys_are_still_accepted(self) -> None:
        issue = IssueData.from_dict({"id": "TD-1", "title": "t", "description": "d", "status": "todo", "assignee": "a@b.com"})
        assert issue.desc == "d"
        assert issue.members == ["a@b.com"]


# ---------------------------------------------------------------------------
# JiraServiceClient._raise_for_status
# ---------------------------------------------------------------------------


class TestRaiseForStatus:
    def _client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_2xx_does_not_raise(self) -> None:
        client = self._client()
        response = _make_response(200, {"status": "ok"})
        client._raise_for_status(response)  # must not raise

    def test_404_raises_service_issue_not_found(self) -> None:
        client = self._client()
        response = _make_response(404, {"detail": "not found"})
        with pytest.raises(ServiceIssueNotFoundError):
            client._raise_for_status(response, issue_id="TD-99")

    def test_404_without_issue_id(self) -> None:
        client = self._client()
        response = _make_response(404)
        with pytest.raises(ServiceIssueNotFoundError, match="Resource not found"):
            client._raise_for_status(response)

    def test_500_raises_service_client_error(self) -> None:
        client = self._client()
        response = _make_response(500, text="internal error")
        with pytest.raises(ServiceClientError):
            client._raise_for_status(response)

    def test_503_raises_service_client_error(self) -> None:
        client = self._client()
        response = _make_response(503, text="unavailable")
        with pytest.raises(ServiceClientError):
            client._raise_for_status(response)


# ---------------------------------------------------------------------------
# JiraServiceClient.health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_status_dict(self) -> None:
        with patch("jira_service_api_client.client.httpx.get") as mock_get:
            mock_get.return_value = _make_response(200, {"status": "ok"})
            client = JiraServiceClient(_BASE, _TOKEN)
            result = client.health()
        assert result == {"status": "ok"}

    def test_raises_on_error(self) -> None:
        with patch("jira_service_api_client.client.httpx.get") as mock_get:
            mock_get.return_value = _make_response(503, text="down")
            client = JiraServiceClient(_BASE, _TOKEN)
            with pytest.raises(ServiceClientError):
                client.health()


# ---------------------------------------------------------------------------
# JiraServiceClient.get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    @pytest.fixture
    def client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_returns_issue_data(self, client: JiraServiceClient) -> None:
        payload = _issue_payload(issue_id="TD-5", title="Found it")
        with patch.object(client._http, "get", return_value=_make_response(200, payload)):
            result = client.get_issue("TD-5")
        assert isinstance(result, IssueData)
        assert result.id == "TD-5"
        assert result.title == "Found it"

    def test_404_raises_not_found(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "get", return_value=_make_response(404)):
            with pytest.raises(ServiceIssueNotFoundError):
                client.get_issue("TD-999")

    def test_500_raises_client_error(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "get", return_value=_make_response(500, text="boom")):
            with pytest.raises(ServiceClientError):
                client.get_issue("TD-1")


# ---------------------------------------------------------------------------
# JiraServiceClient.get_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    @pytest.fixture
    def client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_returns_list_of_issue_data(self, client: JiraServiceClient) -> None:
        body = {"issues": [_issue_payload("TD-1"), _issue_payload("TD-2")], "count": 2}
        with patch.object(client._http, "get", return_value=_make_response(200, body)):
            result = client.get_issues()
        assert len(result) == 2
        assert all(isinstance(i, IssueData) for i in result)

    def test_empty_list(self, client: JiraServiceClient) -> None:
        body = {"issues": [], "count": 0}
        with patch.object(client._http, "get", return_value=_make_response(200, body)):
            result = client.get_issues()
        assert result == []

    def test_passes_filters_as_query_params(self, client: JiraServiceClient) -> None:
        body = {"issues": [], "count": 0}
        mock_get = MagicMock(return_value=_make_response(200, body))
        with patch.object(client._http, "get", mock_get):
            client.get_issues(title="bug", desc="text", members=["alice@example.com"], status=Status.IN_PROGRESS, max_results=5)
        _, call_kwargs = mock_get.call_args
        params: dict[str, Any] = call_kwargs.get("params", {})
        assert params["title"] == "bug"
        assert params["desc"] == "text"
        assert params["members"] == ["alice@example.com"]
        assert params["status"] == "in_progress"
        assert params["max_results"] == 5

    def test_none_filters_omitted_from_params(self, client: JiraServiceClient) -> None:
        body = {"issues": [], "count": 0}
        mock_get = MagicMock(return_value=_make_response(200, body))
        with patch.object(client._http, "get", mock_get):
            client.get_issues()
        _, call_kwargs = mock_get.call_args
        params: dict[str, Any] = call_kwargs.get("params", {})
        assert "title" not in params
        assert "status" not in params


# ---------------------------------------------------------------------------
# JiraServiceClient.create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    @pytest.fixture
    def client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_returns_created_issue(self, client: JiraServiceClient) -> None:
        payload = _issue_payload(issue_id="TD-99", title="New issue")
        with patch.object(client._http, "post", return_value=_make_response(201, payload)):
            result = client.create_issue(title="New issue")
        assert result.id == "TD-99"
        assert result.title == "New issue"

    def test_passes_all_fields(self, client: JiraServiceClient) -> None:
        payload = _issue_payload()
        mock_post = MagicMock(return_value=_make_response(201, payload))
        with patch.object(client._http, "post", mock_post):
            client.create_issue(
                title="T",
                desc="D",
                status=Status.IN_PROGRESS,
                members=["bob@example.com"],
                due_date="2026-01-01",
                board_id="BOARD-1",
            )
        _, call_kwargs = mock_post.call_args
        params: dict[str, Any] = call_kwargs.get("params", {})
        assert params["title"] == "T"
        assert params["desc"] == "D"
        assert params["status"] == "in_progress"
        assert params["members"] == ["bob@example.com"]
        assert params["board_id"] == "BOARD-1"

    def test_500_raises_client_error(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "post", return_value=_make_response(500, text="err")):
            with pytest.raises(ServiceClientError):
                client.create_issue(title="x")


# ---------------------------------------------------------------------------
# JiraServiceClient.update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    @pytest.fixture
    def client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_returns_updated_issue(self, client: JiraServiceClient) -> None:
        payload = _issue_payload(title="Updated")
        with patch.object(client._http, "put", return_value=_make_response(200, payload)):
            result = client.update_issue("TD-1", title="Updated")
        assert result.title == "Updated"

    def test_404_raises_not_found(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "put", return_value=_make_response(404)):
            with pytest.raises(ServiceIssueNotFoundError):
                client.update_issue("TD-999", title="x")

    def test_none_fields_omitted_from_params(self, client: JiraServiceClient) -> None:
        payload = _issue_payload()
        mock_put = MagicMock(return_value=_make_response(200, payload))
        with patch.object(client._http, "put", mock_put):
            client.update_issue("TD-1", title="only-title")
        _, call_kwargs = mock_put.call_args
        params: dict[str, Any] = call_kwargs.get("params", {})
        assert params["title"] == "only-title"
        assert "desc" not in params
        assert "status" not in params

    def test_update_passes_new_fields(self, client: JiraServiceClient) -> None:
        payload = _issue_payload()
        mock_put = MagicMock(return_value=_make_response(200, payload))
        with patch.object(client._http, "put", mock_put):
            client.update_issue("TD-1", desc="D", members=["bob@example.com"], board_id="BOARD-1")
        _, call_kwargs = mock_put.call_args
        params: dict[str, Any] = call_kwargs.get("params", {})
        assert params["desc"] == "D"
        assert params["members"] == ["bob@example.com"]
        assert params["board_id"] == "BOARD-1"


# ---------------------------------------------------------------------------
# JiraServiceClient.delete_issue
# ---------------------------------------------------------------------------


class TestDeleteIssue:
    @pytest.fixture
    def client(self) -> JiraServiceClient:
        return JiraServiceClient(_BASE, _TOKEN)

    def test_success_returns_none(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "delete", return_value=_make_response(200, {})):
            client.delete_issue("TD-1")

    def test_404_raises_not_found(self, client: JiraServiceClient) -> None:
        with patch.object(client._http, "delete", return_value=_make_response(404)):
            with pytest.raises(ServiceIssueNotFoundError):
                client.delete_issue("TD-999")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_enter_returns_self(self) -> None:
        client = JiraServiceClient(_BASE, _TOKEN)
        with client as c:
            assert c is client

    def test_exit_closes_http(self) -> None:
        client = JiraServiceClient(_BASE, _TOKEN)
        mock_close = MagicMock()
        client._http.close = mock_close  # type: ignore[method-assign]
        with client:
            pass
        mock_close.assert_called_once()
