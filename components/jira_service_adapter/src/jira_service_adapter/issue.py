"""Concrete Issue implementation built from service API response data."""

from __future__ import annotations

from typing import Any

from api.issue import Issue, Status

_STATUS_MAP: dict[str, Status] = {
    "to_do": Status.TO_DO,
    "in_progress": Status.IN_PROGRESS,
    "completed": Status.COMPLETED,
}


def _map_status(service_status: str) -> Status:
    return _STATUS_MAP[service_status]


class ServiceIssue(Issue):  # type: ignore[misc]
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
    def desc(self) -> str:
        """Return the issue description."""
        return str(self._data["desc"])

    @property
    def status(self) -> Status:
        """Return the normalised issue status."""
        return _map_status(str(self._data["status"]))

    @property
    def members(self) -> list[str] | None:
        """Return the assigned members or None."""
        return self._data.get("members")

    @property
    def due_date(self) -> str | None:
        """Return the due date or None."""
        return self._data.get("due_date")

    @property
    def board_id(self) -> str:
        """Return the board id.

        The current service payload does not expose board identity.
        """
        raise NotImplementedError
