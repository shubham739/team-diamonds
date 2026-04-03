"""Unit tests for JiraServiceAdapter."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from jira_service_adapter.adapter import JiraServiceAdapter, get_client
from jira_service_adapter.issue import ServiceIssue
from jira_service_api_client.client import ServiceIssueNotFoundError
from jira_service_api_client.models import IssueData
from jira_service_api_client.models import Status as ServiceStatus
from work_mgmt_client_interface.client import IssueNotFoundError
from work_mgmt_client_interface.issue import IssueUpdate, Status

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_data(
    issue_id: str = "TD-1",
    title: str = "Test issue",
    description: str = "A description",
    status: ServiceStatus = ServiceStatus.TODO,
    assignee: str | None = None,
    due_date: str | None = None,
) -> IssueData:
    return IssueData(
        id=issue_id,
        title=title,
        description=description,
        status=status,
        assignee=assignee,
        due_date=due_date,
    )


@pytest.fixture
def mock_http() -> MagicMock:
    """Return a mock JiraServiceClient."""
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
        data = _make_data(status=ServiceStatus.IN_PROGRESS)
        assert ServiceIssue(data).status == Status.IN_PROGRESS

    def test_status_mapping_complete(self) -> None:
        data = _make_data(status=ServiceStatus.COMPLETE)
        assert ServiceIssue(data).status == Status.COMPLETE

    def test_status_mapping_cancelled(self) -> None:
        data = _make_data(status=ServiceStatus.CANCELLED)
        assert ServiceIssue(data).status == Status.CANCELLED

    def test_optional_fields_default_none(self) -> None:
        data = _make_data()
        issue = ServiceIssue(data)
        assert issue.assignee is None
        assert issue.due_date is None


# ---------------------------------------------------------------------------
# JiraServiceAdapter.get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_returns_service_issue(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issue.return_value = _make_data()
        result = adapter.get_issue("TD-1")
        assert isinstance(result, ServiceIssue)
        assert result.id == "TD-1"
        mock_http.get_issue.assert_called_once_with("TD-1")

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.get_issue.side_effect = ServiceIssueNotFoundError("not found")
        with pytest.raises(IssueNotFoundError):
            adapter.get_issue("TD-999")


# ---------------------------------------------------------------------------
# JiraServiceAdapter.get_issues
# ---------------------------------------------------------------------------


class TestGetIssues:
    def test_yields_issues(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.list_issues.return_value = [_make_data("TD-1"), _make_data("TD-2")]
        results = list(adapter.get_issues())
        assert len(results) == 2
        assert all(isinstance(r, ServiceIssue) for r in results)

    def test_passes_filters_to_client(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.list_issues.return_value = []
        list(adapter.get_issues(title="bug", status=Status.IN_PROGRESS, max_results=5))
        mock_http.list_issues.assert_called_once_with(
            title="bug",
            description=None,
            status=ServiceStatus.IN_PROGRESS,
            assignee=None,
            due_date=None,
            max_results=5,
        )

    def test_returns_iterator(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.list_issues.return_value = [_make_data()]
        result = adapter.get_issues()
        assert isinstance(result, Iterator)

    def test_none_status_passes_none(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.list_issues.return_value = []
        list(adapter.get_issues(status=None))
        call_kwargs = mock_http.list_issues.call_args.kwargs
        assert call_kwargs["status"] is None


# ---------------------------------------------------------------------------
# JiraServiceAdapter.create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    def test_returns_created_issue(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.create_issue.return_value = _make_data(title="New issue")
        result = adapter.create_issue(title="New issue")
        assert isinstance(result, ServiceIssue)
        assert result.title == "New issue"

    def test_passes_all_fields(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.create_issue.return_value = _make_data()
        adapter.create_issue(
            title="T",
            description="D",
            status=Status.IN_PROGRESS,
            assignee="bob",
            due_date="2025-01-01",
        )
        mock_http.create_issue.assert_called_once_with(
            title="T",
            description="D",
            status=ServiceStatus.IN_PROGRESS,
            assignee="bob",
            due_date="2025-01-01",
        )


# ---------------------------------------------------------------------------
# JiraServiceAdapter.update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    def test_returns_updated_issue(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.return_value = _make_data(title="Updated")
        update = IssueUpdate(title="Updated")
        result = adapter.update_issue("TD-1", update)
        assert result.title == "Updated"

    def test_only_set_fields_forwarded(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.return_value = _make_data()
        update = IssueUpdate(status=Status.COMPLETE)
        adapter.update_issue("TD-1", update)
        call_kwargs = mock_http.update_issue.call_args.kwargs
        assert call_kwargs["status"] == ServiceStatus.COMPLETE
        assert call_kwargs.get("title") is None

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.update_issue.side_effect = ServiceIssueNotFoundError("not found")
        with pytest.raises(IssueNotFoundError):
            adapter.update_issue("TD-999", IssueUpdate(title="x"))


# ---------------------------------------------------------------------------
# JiraServiceAdapter.delete_issue
# ---------------------------------------------------------------------------


class TestDeleteIssue:
    def test_calls_client_delete(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        adapter.delete_issue("TD-1")
        mock_http.delete_issue.assert_called_once_with("TD-1")

    def test_raises_issue_not_found(self, adapter: JiraServiceAdapter, mock_http: MagicMock) -> None:
        mock_http.delete_issue.side_effect = ServiceIssueNotFoundError("not found")
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
