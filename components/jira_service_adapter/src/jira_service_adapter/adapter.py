"""Adapter that implements IssueTrackerClient via the Jira FastAPI service."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from jira_service_adapter.issue import ServiceIssue
from jira_service_api_client.client import JiraServiceClient, ServiceIssueNotFoundError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from api.board import Board
    from api.issue import Issue, Status

    from jira_service_api_client.models import Status as ServiceStatus



def _to_service_status(status: Status) -> ServiceStatus:
    return status


class IssueNotFoundError(Exception):
    """Raised when an issue cannot be found via the service adapter."""


class JiraServiceAdapter:
    """Implements IssueTrackerClient by delegating to the remote Jira service.

    This is a drop-in replacement for JiraClient. Any consumer that works with
    JiraClient will work identically with JiraServiceAdapter — the only difference
    is that operations are routed through the FastAPI service over HTTP rather than
    calling the Jira API directly.

    Args:
        http_client: A configured JiraServiceClient pointing at the running service.

    """

    def __init__(self, http_client: JiraServiceClient) -> None:
        """Initialise with an HTTP client for the Jira service."""
        self._client = http_client

    # ------------------------------------------------------------------
    # IssueTrackerClient contract
    # ------------------------------------------------------------------

    def get_issue(self, issue_id: str) -> Issue:
        """Fetch a single issue from the remote service.

        Args:
            issue_id: The unique issue identifier.

        Returns:
            An Issue instance.

        Raises:
            IssueNotFoundError: If the service returns 404.

        """
        try:
            data = self._client.get_issue(issue_id)
        except ServiceIssueNotFoundError as exc:
            raise IssueNotFoundError(str(exc)) from exc
        return ServiceIssue(data)

    def get_issues(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        max_results: int = 20,
    ) -> Iterator[Issue]:
        """List issues from the remote service with optional filters.

        Args:
            title: Filter by title substring.
            desc: Filter by description substring.
            status: Filter by status.
            members: Filter by members.
            due_date: Filter by due date.
            max_results: Maximum number of issues to return.

        Yields:
            Issue instances matching the filters.

        """
        service_status = _to_service_status(status) if status is not None else None
        items = self._client.get_issues(
            title=title,
            desc=desc,
            status=service_status,
            members=members,
            due_date=due_date,
            max_results=max_results,
        )
        yield from (ServiceIssue(item) for item in items)

    def create_issue(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        board_id: str | None = None,
    ) -> Issue:
        """Create a new issue via the remote service.

        Args:
            title: Issue title.
            desc: Issue description.
            status: Initial status.
            members: Assigned members.
            due_date: Due date string.
            board_id: Board identifier.

        Returns:
            The newly created Issue.

        """
        service_status = _to_service_status(status) if status is not None else None
        data = self._client.create_issue(
            title=title,
            desc=desc,
            status=service_status,
            members=members,
            due_date=due_date,
            board_id=board_id,
        )
        return ServiceIssue(data)

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
        """Apply a partial update to an existing issue via the remote service.

        Args:
            issue_id: Unique identifier of the issue to update.
            title: Issue title.
            desc: Issue description.
            members: Assigned members.
            due_date: Due date string.
            status: Issue status.
            board_id: Board identifier.

        Returns:
            The updated Issue.

        Raises:
            IssueNotFoundError: If the issue does not exist.

        """
        service_status = _to_service_status(status) if status is not None else None

        try:
            data = self._client.update_issue(
                issue_id,
                title=title,
                desc=desc,
                status=service_status,
                members=members,
                due_date=due_date,
                board_id=board_id,
            )
        except ServiceIssueNotFoundError as exc:
            raise IssueNotFoundError(str(exc)) from exc
        return ServiceIssue(data)

    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue via the remote service.

        Args:
            issue_id: Unique identifier of the issue to delete.

        Raises:
            IssueNotFoundError: If the issue does not exist.

        """
        try:
            self._client.delete_issue(issue_id)
        except ServiceIssueNotFoundError as exc:
            raise IssueNotFoundError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Board and List access — not yet exposed by the HTTP service
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Board:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError

    def get_boards(self) -> Iterator[Board]:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError

    def get_list(self, list_id: str) -> List:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError

    def get_lists(self, board_id: str) -> Iterator[List]:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError


    # ------------------------------------------------------------------
    # Board and List access — not yet exposed by the HTTP service
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Board:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError

    def get_boards(self) -> Iterator[Board]:
        """Not yet implemented for the remote service adapter."""
        raise NotImplementedError

def get_client(*, interactive: bool = False) -> JiraServiceAdapter:  # noqa: ARG001
    """Create a JiraServiceAdapter from environment variables.

    Environment variables:
        JIRA_SERVICE_BASE_URL:    Base URL of the running Jira service.
        JIRA_SERVICE_ACCESS_TOKEN: OAuth2 bearer token for authentication.

    Args:
        interactive: Unused — provided for interface compatibility.

    Returns:
        A configured JiraServiceAdapter.

    Raises:
        OSError: If required environment variables are missing.

    """
    base_url = os.environ.get("JIRA_SERVICE_BASE_URL", "")
    access_token = os.environ.get("JIRA_SERVICE_ACCESS_TOKEN", "")

    missing = [
        name
        for name, val in [
            ("JIRA_SERVICE_BASE_URL", base_url),
            ("JIRA_SERVICE_ACCESS_TOKEN", access_token),
        ]
        if not val
    ]
    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        raise OSError(msg)

    http_client = JiraServiceClient(base_url=base_url, access_token=access_token)
    return JiraServiceAdapter(http_client)
