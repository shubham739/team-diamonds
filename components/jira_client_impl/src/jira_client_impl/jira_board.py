from jira_client_impl.jira_issue import JiraIssue, get_issue as _make_issue
from jira_client_impl.jira_impl import JiraClient, JiraError
from work_mgmt_client_interface.src.work_mgmt_client_interface.issue import Status, Issue, IssueUpdate
from work_mgmt_client_interface.src.work_mgmt_client_interface.board import Board, BoardColumn

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional



@dataclass
class JiraBoard(Board):

    _board_id: str
    _name: str
    _client: JiraClient

    _columns: list[BoardColumn] = field(
        default_factory=lambda: [
            BoardColumn(Status.TODO, "To Do"),
            BoardColumn(Status.IN_PROGRESS, "In Progress"),
            BoardColumn(Status.COMPLETE, "Done"),
            BoardColumn(Status.CANCELLED, "Cancelled"),
        ]
    )

    @property
    def id(self) -> str:
        return self._board_id
    
    @property
    def name(self) -> str:
        return self._name
    @property
    def columns(self) -> list[BoardColumn]:
        return list(self._columns)
    
    def list_issues(self, *, status: Status | None = None) -> list[Issue]:
        """
        Fetch issues for this board using the Jira Agile API:
          GET /rest/agile/1.0/board/{boardId}/issue

        Returns Issue objects (your JiraIssue adapter) by reusing JiraClient._build_issue().
        """
        issues = self._get_board_issues(fields="summary,description,status,assignee,duedate")

        # Convert raw Agile "issues" to JiraIssue instances using your JiraClient
        built: list[Issue] = [self._client._build_issue(i) for i in issues]  # type: ignore[attr-defined]

        if status is None:
            return built
        return [i for i in built if i.status == status]

    def get_issue(self, issue_id: str) -> Issue:
        """Delegate to JiraClient (Platform API v3) to fetch a single issue."""
        return self._client.get_issue(issue_id)
    
