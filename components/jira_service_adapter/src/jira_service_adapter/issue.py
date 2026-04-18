"""Concrete Issue implementation built from service API response data."""

from __future__ import annotations

from typing import Any

from work_mgmt_client_interface.issue import Issue, Status

_STATUS_MAP: dict[str, Status] = {
    "to_do": Status.TODO,
    "in_progress": Status.IN_PROGRESS,
    "completed": Status.COMPLETE,
}


def _map_status(raw: str) -> Status:
    return _STATUS_MAP.get(raw, Status.TODO)


class ServiceIssue(Issue):
    """Issue implementation that wraps a remote service response.

    Args:
        data: The raw issue data dict returned by the Jira service.

    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialise from service response data."""
        self._data = data

    @property
    def id(self) -> str:
        """Return the issue ID."""
        return str(self._data["id"])

    @property
    def title(self) -> str:
        """Return the issue title."""
        return str(self._data["title"])

    @property
    def description(self) -> str:
        """Return the issue description."""
        return str(self._data["description"])

    @property
    def status(self) -> Status:
        """Return the normalised issue status."""
        return _map_status(str(self._data["status"]))

    @property
    def assignee(self) -> str | None:
        """Return the assignee or None."""
        v = self._data.get("assignee")
        return str(v) if v is not None else None

    @property
    def due_date(self) -> str | None:
        """Return the due date or None."""
        v = self._data.get("due_date")
        return str(v) if v is not None else None
