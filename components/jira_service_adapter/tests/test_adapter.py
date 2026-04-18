"""Unit tests for JiraServiceAdapter."""

from __future__ import annotations

from collections.abc import Iterator
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from jira_service_adapter.adapter import JiraServiceAdapter, ServiceClientError, get_client
from jira_service_adapter.issue import ServiceIssue
from jira_service_api_client.models.status import Status as ServiceStatus
from work_mgmt_client_interface.client import IssueNotFoundError
from work_mgmt_client_interface.issue import IssueUpdate, Status

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_data(
    issue_id: str = "TD-1",
    title: str = "Test issue",
    description: str = "A description",
    status: str = "to_do",
    assignee: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "title": title,
        "description": description,
        "status": status,
        "assignee": assignee,
        "due_date": due_date,
    }


def _make_api_response(status_code: HTTPStatus, data: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.parsed = MagicMock()
    resp.parsed.additional_properties = data
    return resp


@pytest.fixture
def mock_http() -> MagicMock:
    """Return a mock AuthenticatedClient."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http: MagicMock) -> JiraServiceAdapter:
    """Return an adapter wired to the mock HTTP client."""
    return JiraServiceAdapter(mock_http)


# ---------------------------------------------------------------------------
# ServiceIssue
# ---------------------------------------------------------------------------


class TestServiceIssue:
    def test_properties_populated_correctly(self) -> None:
        data = _make_data(assignee="alice@example.com", due_date="2025-12-31")
        issue = ServiceIssue(data)
        assert issue.id == "TD-1"
        assert issue.title == "Test issue"
        assert issue.description == "A description"
        assert issue.status == Status.TODO
        assert issue.assignee == "alice@example.com"
        assert issue.due_date == "2025-12-31"

    def test_status_mapping_in_progress(self) -> None:
        data = _make_data(status="in_progress")
        assert ServiceIssue(data).status == Status.IN_PROGRESS

    def test_status_mapping_complete(self) -> None:
        data = _make_data(status="completed")
        assert ServiceIssue(data).status == Status.COMPLETE

    def test_unknown_status_defaults_to_todo(self) -> None:
        data = _make_data(status="unknown_value")
        assert ServiceIssue(data).status == Status.TODO

    def test_optional_fields_default_none(self) -> None:
        data = _make_data()
        issue = ServiceIssue(data)
        assert issue.assignee is None
        assert issue.due_date is None


# ---------------------------------------------------------------------------
# JiraServiceAdapter.get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_returns_service_issue(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, _make_data())
        with patch("jira_service_adapter.adapter.get_issue_issues_issue_id_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            result = adapter.get_issue("TD-1")
        assert isinstance(result, ServiceIssue)
        assert result.id == "TD-1"
        mock_ep.sync_detailed.assert_called_once_with("TD-1", client=adapter._client)

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.NOT_FOUND, {})
        with patch("jira_service_adapter.adapter.get_issue_issues_issue_id_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            with pytest.raises(IssueNotFoundError):
                adapter.get_issue("TD-999")

    def test_raises_service_client_error_on_server_error(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.INTERNAL_SERVER_ERROR, {})
        with patch("jira_service_adapter.adapter.get_issue_issues_issue_id_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            with pytest.raises(ServiceClientError):
                adapter.get_issue("TD-1")


# ---------------------------------------------------------------------------
# JiraServiceAdapter.get_issues
# ---------------------------------------------------------------------------


class TestGetIssues:
    def test_yields_issues(self, adapter: JiraServiceAdapter) -> None:
        payload = {"issues": [_make_data("TD-1"), _make_data("TD-2")]}
        resp = _make_api_response(HTTPStatus.OK, payload)
        with patch("jira_service_adapter.adapter.list_issues_issues_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            results = list(adapter.get_issues())
        assert len(results) == 2
        assert all(isinstance(r, ServiceIssue) for r in results)

    def test_passes_filters_to_endpoint(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, {"issues": []})
        with patch("jira_service_adapter.adapter.list_issues_issues_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            list(adapter.get_issues(title="bug", status=Status.IN_PROGRESS, max_results=5))
        call_kwargs = mock_ep.sync_detailed.call_args.kwargs
        assert call_kwargs["title"] == "bug"
        assert call_kwargs["status"] == ServiceStatus.IN_PROGRESS
        assert call_kwargs["max_results"] == 5

    def test_maps_assignee_to_members_list(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, {"issues": []})
        with patch("jira_service_adapter.adapter.list_issues_issues_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            list(adapter.get_issues(assignee="bob@example.com"))
        call_kwargs = mock_ep.sync_detailed.call_args.kwargs
        assert call_kwargs["members"] == ["bob@example.com"]

    def test_returns_iterator(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, {"issues": [_make_data()]})
        with patch("jira_service_adapter.adapter.list_issues_issues_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            result = adapter.get_issues()
        assert isinstance(result, Iterator)

    def test_none_status_passes_none(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, {"issues": []})
        with patch("jira_service_adapter.adapter.list_issues_issues_get") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            list(adapter.get_issues(status=None))
        call_kwargs = mock_ep.sync_detailed.call_args.kwargs
        assert call_kwargs["status"] is None


# ---------------------------------------------------------------------------
# JiraServiceAdapter.create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    def test_returns_created_issue(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.CREATED, _make_data(title="New issue"))
        with patch("jira_service_adapter.adapter.create_issue_issues_post") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            result = adapter.create_issue(title="New issue")
        assert isinstance(result, ServiceIssue)
        assert result.title == "New issue"

    def test_passes_all_fields(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.CREATED, _make_data())
        with patch("jira_service_adapter.adapter.create_issue_issues_post") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            adapter.create_issue(
                title="T",
                description="D",
                status=Status.IN_PROGRESS,
                assignee="bob",
                due_date="2025-01-01",
            )
        call_kwargs = mock_ep.sync_detailed.call_args.kwargs
        body = call_kwargs["body"]
        assert body.title == "T"
        assert body.desc == "D"
        assert body.status == ServiceStatus.IN_PROGRESS
        assert body.members == ["bob"]
        assert body.due_date == "2025-01-01"


# ---------------------------------------------------------------------------
# JiraServiceAdapter.update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    def test_returns_updated_issue(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, _make_data(title="Updated"))
        with patch("jira_service_adapter.adapter.update_issue_issues_issue_id_put") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            result = adapter.update_issue("TD-1", IssueUpdate(title="Updated"))
        assert result.title == "Updated"

    def test_only_set_fields_forwarded(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, _make_data())
        with patch("jira_service_adapter.adapter.update_issue_issues_issue_id_put") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            adapter.update_issue("TD-1", IssueUpdate(status=Status.COMPLETE))
        call_kwargs = mock_ep.sync_detailed.call_args.kwargs
        body = call_kwargs["body"]
        assert body.status == ServiceStatus.COMPLETED
        assert body.title is None

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.NOT_FOUND, {})
        with patch("jira_service_adapter.adapter.update_issue_issues_issue_id_put") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            with pytest.raises(IssueNotFoundError):
                adapter.update_issue("TD-999", IssueUpdate(title="x"))


# ---------------------------------------------------------------------------
# JiraServiceAdapter.delete_issue
# ---------------------------------------------------------------------------


class TestDeleteIssue:
    def test_calls_endpoint_delete(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.OK, {})
        with patch("jira_service_adapter.adapter.delete_issue_issues_issue_id_delete") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            adapter.delete_issue("TD-1")
        mock_ep.sync_detailed.assert_called_once_with("TD-1", client=adapter._client)

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter) -> None:
        resp = _make_api_response(HTTPStatus.NOT_FOUND, {})
        with patch("jira_service_adapter.adapter.delete_issue_issues_issue_id_delete") as mock_ep:
            mock_ep.sync_detailed.return_value = resp
            with pytest.raises(IssueNotFoundError):
                adapter.delete_issue("TD-999")


# ---------------------------------------------------------------------------
# get_client factory
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_raises_if_env_vars_missing(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(OSError, match="Missing required environment variables"):
                get_client()

    def test_raises_if_only_base_url_set(self) -> None:
        with patch.dict("os.environ", {"JIRA_SERVICE_BASE_URL": "http://localhost:8000"}, clear=True):
            with pytest.raises(OSError, match="JIRA_SERVICE_ACCESS_TOKEN"):
                get_client()

    def test_returns_adapter_when_env_vars_present(self) -> None:
        env = {
            "JIRA_SERVICE_BASE_URL": "http://localhost:8000",
            "JIRA_SERVICE_ACCESS_TOKEN": "test-token",
        }
        with patch.dict("os.environ", env, clear=True):
            client = get_client()
        assert isinstance(client, JiraServiceAdapter)
