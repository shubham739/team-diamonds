"""Response models for the Jira Service API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.issue import Status as Status  # noqa: PLC0414


def _parse_status(raw_status: object) -> Status:
    """Parse service status values into the external API's enum."""
    normalized = str(raw_status or Status.TO_DO.value).strip().lower()
    legacy_map = {
        "todo": Status.TO_DO,
        "to_do": Status.TO_DO,
        "in_progress": Status.IN_PROGRESS,
        "complete": Status.COMPLETED,
        "completed": Status.COMPLETED,
        "cancelled": Status.COMPLETED,
        "canceled": Status.COMPLETED,
    }
    return legacy_map.get(normalized, Status.TO_DO)


@dataclass
class IssueData:
    """Data returned by the service for a single issue."""

    id: str
    title: str
    desc: str
    status: Status
    members: list[str] | None
    due_date: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueData:
        """Construct an IssueData from a raw API response dict."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            desc=str(data.get("desc") or data.get("description") or ""),
            status=_parse_status(data.get("status")),
            members=_parse_members(data),
            due_date=data.get("due_date"),
        )


def _parse_members(data: dict[str, Any]) -> list[str] | None:
    """Parse members from either the new or legacy response shape."""
    raw_members = data.get("members")
    if isinstance(raw_members, list):
        members = [str(member) for member in raw_members if member is not None]
        return members or None

    raw_assignee = data.get("assignee")
    if raw_assignee is None:
        return None

    return [str(raw_assignee)]


@dataclass
class HealthResponse:
    """Response from the /health endpoint."""

    status: str
