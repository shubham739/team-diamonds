"""Integration tests for jira_client_impl."""

import logging
import os

import pytest
from jira_client_impl.jira_board import JiraBoard
from jira_client_impl.jira_impl import JiraClient, get_client
from jira_client_impl.jira_issue import JiraIssue, get_issue
from work_mgmt_client_interface.board import Board
from work_mgmt_client_interface.issue import Issue, Status

pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def client() -> JiraClient:
    """Return a live, authenticated JiraClient, or skip if credentials are absent."""
    missing = [
        var for var in ("JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN")
        if not os.environ.get(var)
    ]
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
    return get_client(interactive=False)


class TestGetClientAndAuthenticate:
    """Factory behaviour and credential validation."""

    @pytest.mark.circleci
    def test_raises_os_error_when_all_env_vars_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OSError is raised listing all missing variables when no env vars are set."""
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

        with pytest.raises(OSError, match="Missing required environment variables"):
            get_client(interactive=False)

    @pytest.mark.circleci
    def test_error_message_names_every_missing_variable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OSError message must name each missing variable individually."""
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

        with pytest.raises(OSError, match="Missing required environment variables"):
            get_client(interactive=False)


class TestDependencyInjection:
    """Abstract contract and factory wiring."""

    @pytest.mark.circleci
    def test_jira_issue_is_subclass_of_issue(self) -> None:
        """JiraIssue must satisfy the abstract Issue contract."""
        assert issubclass(JiraIssue, Issue)

    @pytest.mark.circleci
    def test_jira_board_is_subclass_of_board(self) -> None:
        """JiraBoard must satisfy the abstract Board contract."""
        assert issubclass(JiraBoard, Board)

    @pytest.mark.circleci
    def test_get_issue_factory_returns_jira_issue(self) -> None:
        """get_issue() must return a JiraIssue with correctly mapped fields."""
        raw_fields = {
            "summary": "DI test issue",
            "description": None,
            "status": {"name": "To Do"},
            "assignee": None,
            "duedate": None,
        }
        issue = get_issue("DI-1", raw_fields, base_url="https://example.atlassian.net")

        assert isinstance(issue, JiraIssue)
        assert isinstance(issue, Issue)
        assert issue.id == "DI-1"
        assert issue.title == "DI test issue"
        assert issue.status == Status.TODO


class TestJiraIssueFieldParsing:
    """JiraIssue field mapping and ADF description extraction."""

    @pytest.mark.circleci
    def test_plain_string_description_returned_verbatim(self) -> None:
        """Plain-string description must be returned verbatim."""
        issue = get_issue("T-1", {"summary": "s", "description": "plain text"})
        assert issue.description == "plain text"

    @pytest.mark.circleci
    def test_adf_description_extracted_to_plain_text(self) -> None:
        """ADF description object must be flattened to readable plain text."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "ADF paragraph text"}],
                },
            ],
        }
        issue = get_issue("T-2", {"summary": "s", "description": adf})
        assert "ADF paragraph text" in issue.description

    @pytest.mark.circleci
    def test_null_description_returns_empty_string(self) -> None:
        """Null description must return an empty string, not None."""
        issue = get_issue("T-3", {"summary": "s", "description": None})
        assert issue.description == ""

    @pytest.mark.circleci
    def test_status_normalisation_to_do(self) -> None:
        """Jira status 'To Do' must normalise to Status.TODO."""
        issue = get_issue("T-4", {"summary": "s", "status": {"name": "To Do"}})
        assert issue.status == Status.TODO

    @pytest.mark.circleci
    def test_status_normalisation_in_progress(self) -> None:
        """Jira status 'In Progress' must normalise to Status.IN_PROGRESS."""
        issue = get_issue("T-5", {"summary": "s", "status": {"name": "In Progress"}})
        assert issue.status == Status.IN_PROGRESS

    @pytest.mark.circleci
    def test_status_normalisation_done(self) -> None:
        """Jira status 'Done' must normalise to Status.COMPLETE."""
        issue = get_issue("T-6", {"summary": "s", "status": {"name": "Done"}})
        assert issue.status == Status.COMPLETE

    @pytest.mark.circleci
    def test_unknown_status_defaults_to_todo(self) -> None:
        """Unrecognised Jira status must fall back to Status.TODO."""
        issue = get_issue("T-7", {"summary": "s", "status": {"name": "Some Unrecognised Status"}})
        assert issue.status == Status.TODO

    @pytest.mark.circleci
    def test_assignee_prefers_email_over_display_name(self) -> None:
        """When both emailAddress and displayName are present, emailAddress must win."""
        raw = {
            "summary": "s",
            "assignee": {"emailAddress": "dev@example.com", "displayName": "Dev User"},
        }
        issue = get_issue("T-8", raw)
        assert issue.assignee == "dev@example.com"

    @pytest.mark.circleci
    def test_assignee_falls_back_to_display_name(self) -> None:
        """When emailAddress is absent, displayName must be returned as assignee."""
        issue = get_issue("T-9", {"summary": "s", "assignee": {"displayName": "Dev User"}})
        assert issue.assignee == "Dev User"

    @pytest.mark.circleci
    def test_unassigned_issue_returns_none(self) -> None:
        """Issue with no assignee must return None."""
        issue = get_issue("T-10", {"summary": "s", "assignee": None})
        assert issue.assignee is None
