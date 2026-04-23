"""Unit tests for JiraServiceAdapter."""

from __future__ import annotations

from collections.abc import Iterator
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from api.issue import Status

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
    desc: str = "A description",
    status: ServiceStatus = ServiceStatus.TO_DO,
    members: list[str] | None = None,
    due_date: str | None = None,
) -> IssueData:
    return IssueData(
        id=issue_id,
        title=title,
        desc=desc,
        status=status,
        members=members,
        due_date=due_date,
    )


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
        data = _make_data(members=["alice@example.com"], due_date="2025-12-31")
        issue = ServiceIssue(data)
        assert issue.id == "TD-1"
        assert issue.title == "Test issue"
        assert issue.desc == "A description"
        assert issue.status == Status.TO_DO
        assert issue.members == ["alice@example.com"]
        assert issue.due_date == "2025-12-31"

    def test_status_mapping_in_progress(self) -> None:
        data = _make_data(status="in_progress")
        assert ServiceIssue(data).status == Status.IN_PROGRESS

    def test_status_mapping_complete(self) -> None:
        data = _make_data(status=ServiceStatus.COMPLETED)
        assert ServiceIssue(data).status == Status.COMPLETED

    def test_status_mapping_completed(self) -> None:
        data = _make_data(status=ServiceStatus.COMPLETED)
        assert ServiceIssue(data).status == Status.COMPLETED

    def test_optional_fields_default_none(self) -> None:
        data = _make_data()
        issue = ServiceIssue(data)
        assert issue.members is None
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
    def test_yields_issues(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issues.return_value = [_make_data("TD-1"), _make_data("TD-2")]
        results = list(adapter.get_issues())
        assert len(results) == 2
        assert all(isinstance(r, ServiceIssue) for r in results)

    def test_passes_filters_to_client(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issues.return_value = []
        list(adapter.get_issues(title="bug", desc="D", members=["alice@example.com"], status=Status.IN_PROGRESS, max_results=5))
        mock_http.get_issues.assert_called_once_with(
            title="bug",
            desc="D",
            status=ServiceStatus.IN_PROGRESS,
            members=["alice@example.com"],
            due_date=None,
            max_results=5,
        )

    def test_returns_iterator(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issues.return_value = [_make_data()]
        result = adapter.get_issues()
        assert isinstance(result, Iterator)

    def test_none_status_passes_none(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issues.return_value = []
        list(adapter.get_issues(status=None))
        call_kwargs = mock_http.get_issues.call_args.kwargs
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

    def test_passes_all_fields(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.create_issue.return_value = _make_data()
        adapter.create_issue(
            title="T",
            desc="D",
            status=Status.IN_PROGRESS,
            members=["bob"],
            due_date="2025-01-01",
            board_id="BOARD-1",
        )
        mock_http.create_issue.assert_called_once_with(
            title="T",
            desc="D",
            status=ServiceStatus.IN_PROGRESS,
            members=["bob"],
            due_date="2025-01-01",
            board_id="BOARD-1",
        )


# ---------------------------------------------------------------------------
# JiraServiceAdapter.update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    def test_returns_updated_issue(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.return_value = _make_data(title="Updated")
        result = adapter.update_issue("TD-1", title="Updated")
        assert result.title == "Updated"

    def test_only_set_fields_forwarded(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.return_value = _make_data()
        adapter.update_issue("TD-1", status=Status.COMPLETED)
        call_kwargs = mock_http.update_issue.call_args.kwargs
        assert call_kwargs["status"] == ServiceStatus.COMPLETED
        assert call_kwargs.get("title") is None

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.side_effect = ServiceIssueNotFoundError("not found")
        with pytest.raises(IssueNotFoundError):
            adapter.update_issue("TD-999", title="x")


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
