"""Implementation of Jira Board which is needed for issue tracking with Jira."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from api.board import Board
from api.issue import Issue, Status

if TYPE_CHECKING:
    from jira_client_impl.jira_impl import JiraClient

@dataclass(frozen=True)
class JiraColumn:
    """Lightweight board column descriptor used by JiraBoard."""

    status: Status
    name: str

@dataclass(frozen=True)
class JiraColumn:
    """Lightweight board column descriptor used by JiraBoard."""

    status: Status
    name: str


@dataclass
class JiraBoard(Board):  # type: ignore[misc]
    """Implementation of Jira Board which is needed for issue tracking with Jira."""

    _board_id: str
    _name: str
    _client: JiraClient

    _columns: list[JiraColumn] = field(
        default_factory=lambda: [
            JiraColumn(Status.TO_DO, "To Do"),
            JiraColumn(Status.IN_PROGRESS, "In Progress"),
            JiraColumn(Status.COMPLETED, "Done"),
        ],
    )

    @property
    def id(self) -> str:
        """Return id."""
        return self._board_id

    @property
    def board_name(self) -> str:
        """Return board name required by the external Board contract."""
        return self._name

    @property
    def name(self) -> str:
        """Backward-compatible alias for board_name."""
        return self.board_name

    @property
    def columns(self) -> list[JiraColumn]:
        """Return columns."""
        return list(self._columns)

    def get_issues(self, *, status: Status | None = None) -> list[Issue]:
        """Fetch issues for this board using the Jira Agile API.

          GET /rest/agile/1.0/board/{boardId}/issue

        Returns Issue objects (your JiraIssue adapter) by reusing JiraClient.build_issue().
        """
        data = self._client._agile_get(  # noqa: SLF001
            f"/board/{self._board_id}/issue",
            params={"fields": "summary,description,status,assignee,duedate"},
        )
        if not isinstance(data, dict):
            return []

        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            return []

        # Convert raw Agile "issues" to JiraIssue instances using your JiraClient
        built: list[Issue] = [self._client.build_issue(i) for i in raw_issues if isinstance(i, dict)]

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
        desc: str = "",
        status: Status = Status.TO_DO,
        members: list[str] | None = None,
        due_date: str | None = None,
        board_id: str | None = None,
    ) -> Issue:
        """Create a new issue on the board by delegating to JiraClient."""
        return self._client.create_issue(
            title=title,
            desc=desc,
            status=status,
            members=members,
            due_date=due_date,
            board_id=board_id,
        )

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status | None = None,
        board_id: str | None = None,
    ) -> Issue:
        """Update an issue on the board by delegating to JiraClient."""
        return self._client.update_issue(
            issue_id,
            title=title,
            desc=desc,
            members=members,
            due_date=due_date,
            status=status,
            board_id=board_id,
        )

    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue from the board by delegating to JiraClient."""
        self._client.delete_issue(issue_id)
