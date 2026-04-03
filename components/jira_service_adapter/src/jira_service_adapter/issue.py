"""Concrete Issue implementation built from service API response data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from work_mgmt_client_interface.issue import Issue, Status

if TYPE_CHECKING:
    from jira_service_api_client.models import IssueData
    from jira_service_api_client.models import Status as ServiceStatus


def _map_status(service_status: ServiceStatus) -> Status:
    return Status(service_status.value)


class ServiceIssue(Issue):
    """Issue implementation that wraps a remote service response.

    Args:
        data: The IssueData returned by the JiraServiceClient.

    """

    def __init__(self, data: IssueData) -> None:
        """Initialise from service response data."""
        self._data = data

    @property
    def id(self) -> str:
        """Return the issue ID."""
        return self._data.id

    @property
    def title(self) -> str:
        """Return the issue title."""
        return self._data.title

    @property
    def description(self) -> str:
        """Return the issue description."""
        return self._data.description

    @property
    def status(self) -> Status:
        """Return the normalised issue status."""
        return _map_status(self._data.status)

    @property
    def assignee(self) -> str | None:
        """Return the assignee or None."""
        return self._data.assignee

    @property
    def due_date(self) -> str | None:
        """Return the due date or None."""
        return self._data.due_date
