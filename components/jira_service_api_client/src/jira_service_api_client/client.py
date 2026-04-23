"""HTTP client for the Jira FastAPI service."""

from __future__ import annotations

from typing import Any, Self

import httpx

from jira_service_api_client.models import IssueData, Status


class ServiceClientError(Exception):
    """Raised when the service returns an unexpected response."""


class ServiceIssueNotFoundError(ServiceClientError):
    """Raised when the service returns a 404 for an issue."""


class JiraServiceClient:
    """Type-safe HTTP client for the Jira service API.

    Args:
        base_url: Base URL of the running Jira service (e.g. https://my-service.fly.dev).
        access_token: OAuth2 bearer token for authenticated endpoints.

    """

    def __init__(self, base_url: str, access_token: str) -> None:
        """Initialise the client with a base URL and bearer token."""
        self._base_url = base_url.rstrip("/")
        self._access_token = access_token
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=30.0,
        )

    def _raise_for_status(self, response: httpx.Response, issue_id: str | None = None) -> None:
        if response.status_code == 404:  # noqa: PLR2004
            msg = f"Issue {issue_id} not found" if issue_id else "Resource not found"
            raise ServiceIssueNotFoundError(msg)
        if not response.is_success:
            msg = f"Service error {response.status_code}: {response.text}"
            raise ServiceClientError(msg)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict[str, str]:
        """Check service health. Does not require authentication."""
        response = httpx.get(f"{self._base_url}/health", timeout=10.0)
        self._raise_for_status(response)
        result: dict[str, str] = response.json()
        return result

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def get_issue(self, issue_id: str) -> IssueData:
        """Fetch a single issue by ID."""
        response = self._http.get(f"/issues/{issue_id}")
        self._raise_for_status(response, issue_id=issue_id)
        return IssueData.from_dict(response.json())

    def get_issues(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        max_results: int = 20,
    ) -> list[IssueData]:
        """Get issues with optional filters."""
        params: dict[str, Any] = {"max_results": max_results}
        if title is not None:
            params["title"] = title
        if desc is not None:
            params["desc"] = desc
        if status is not None:
            params["status"] = status.value
        if members is not None:
            params["members"] = members
        if due_date is not None:
            params["due_date"] = due_date

        response = self._http.get("/issues", params=params)
        self._raise_for_status(response)
        data: dict[str, Any] = response.json()
        return [IssueData.from_dict(item) for item in data.get("issues", [])]

    def create_issue(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        board_id: str | None = None,
    ) -> IssueData:
        """Create a new issue."""
        params: dict[str, Any] = {}
        if title is not None:
            params["title"] = title
        if desc is not None:
            params["desc"] = desc
        if status is not None:
            params["status"] = status.value
        if members is not None:
            params["members"] = members
        if due_date is not None:
            params["due_date"] = due_date
        if board_id is not None:
            params["board_id"] = board_id

        response = self._http.post("/issues", params=params)
        self._raise_for_status(response)
        return IssueData.from_dict(response.json())

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        board_id: str | None = None,
    ) -> IssueData:
        """Update an existing issue."""
        params: dict[str, Any] = {}
        if title is not None:
            params["title"] = title
        if desc is not None:
            params["desc"] = desc
        if status is not None:
            params["status"] = status.value
        if members is not None:
            params["members"] = members
        if due_date is not None:
            params["due_date"] = due_date
        if board_id is not None:
            params["board_id"] = board_id

        response = self._http.put(f"/issues/{issue_id}", params=params)
        self._raise_for_status(response, issue_id=issue_id)
        return IssueData.from_dict(response.json())

    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue by ID."""
        response = self._http.delete(f"/issues/{issue_id}")
        self._raise_for_status(response, issue_id=issue_id)

    def __enter__(self) -> Self:
        """Support use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close underlying HTTP connection on exit."""
        self._http.close()
