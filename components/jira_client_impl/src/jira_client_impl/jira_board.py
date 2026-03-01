"""Implementation of Jira Board which is needed for issue tracking with Jira."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from work_mgmt_client_interface.board import Board, BoardColumn
from work_mgmt_client_interface.issue import Issue, IssueUpdate, Status

if TYPE_CHECKING:
    from jira_client_impl.jira_impl import JiraClient

@dataclass
class JiraBoard(Board):
    """Implementation of Jira Board which is needed for issue tracking with Jira."""

    _board_id: str
    _name: str
    _client: JiraClient

    _columns: list[BoardColumn] = field(
        default_factory=lambda: [
            BoardColumn(Status.TODO, "To Do"),
            BoardColumn(Status.IN_PROGRESS, "In Progress"),
            BoardColumn(Status.COMPLETE, "Done"),
            BoardColumn(Status.CANCELLED, "Cancelled"),
        ],
    )

    @property
    def id(self) -> str:
        """Return id."""
        return self._board_id

    @property
    def name(self) -> str:
        """Return name."""
        return self._name
    @property
    def columns(self) -> list[BoardColumn]:
        """Return columns."""
        return list(self._columns)

    def list_issues(self, *, status: Status | None = None) -> list[Issue]:
        """Fetch issues for this board using the Jira Agile API.

          GET /rest/agile/1.0/board/{boardId}/issue

        Returns Issue objects (your JiraIssue adapter) by reusing JiraClient.build_issue().
        """
        data = self._client._get( # noqa: SLF001
            f"/board/{self._board_id}/issue",
            params={"fields": "summary,description,status,assignee,duedate"},
        )
        if not isinstance(data, dict):
            return []

        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            return []

        # Convert raw Agile "issues" to JiraIssue instances using your JiraClient
        built: list[Issue] = [
            self._client.build_issue(i)
            for i in raw_issues if isinstance(i, dict)]

        if status is None:
            return built
        return [i for i in built if i.status == status]

    def get_issue(self, issue_id: str) -> Issue:
        """Delegate to JiraClient (Platform API v3) to fetch a single issue."""
        return self._client.get_issue(issue_id)

    def create_issue(
        self,
        *,
        title: str,
        description: str = "",
        status: Status = Status.TODO,
    ) -> Issue:
        """Create a new issue on the board by delegating to JiraClient."""
        return self._client.create_issue(
            title=title,
            description=description,
            status=status,
        )

    def update_issue(self, issue_id: str, update: IssueUpdate) -> Issue:
        """Update an issue on the board by delegating to JiraClient."""
        return self._client.update_issue(issue_id, update)

    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue from the board (not yet implemented in JiraClient)."""
        # TODO: Implement delete_issue in JiraClient when the API endpoint is available # noqa: FIX002, TD003, TD002
        msg = "delete_issue is not yet implemented"
        raise NotImplementedError(msg)
