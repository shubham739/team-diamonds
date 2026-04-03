"""Response models for the Jira Service API client."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    """Issue status values returned by the service."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


@dataclass
class IssueData:
    """Data returned by the service for a single issue."""

    id: str
    title: str
    description: str
    status: Status
    assignee: str | None
    due_date: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueData:
        """Construct an IssueData from a raw API response dict."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description") or ""),
            status=Status(data.get("status", "todo")),
            assignee=data.get("assignee"),
            due_date=data.get("due_date"),
        )


@dataclass
class HealthResponse:
    """Response from the /health endpoint."""

    status: str
