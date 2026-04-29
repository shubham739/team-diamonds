"""Jira Issue implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from api.issue import Issue, Status

if TYPE_CHECKING:
    from jira_client_impl.jira_impl import JiraClient

# ---------------------------------------------------------------------------
# Mapping tables: Jira-native values  →  normalized enum values
# ---------------------------------------------------------------------------

# to clean user's input into a standardized status that is used across all implementations
_JIRA_STATUS_MAP: dict[str, Status] = {
    # to do
    "to do": Status.TO_DO,
    "open": Status.TO_DO,
    "backlog": Status.TO_DO,
    "new": Status.TO_DO,
    # in progress
    "in progress": Status.IN_PROGRESS,
    "working": Status.IN_PROGRESS,
    "development": Status.IN_PROGRESS,
    # done
    "complete": Status.COMPLETED,
    "done": Status.COMPLETED,
    "closed": Status.COMPLETED,
    "resolved": Status.COMPLETED,
    "cancelled": Status.COMPLETED,
    "canceled": Status.COMPLETED,
    "rejected": Status.COMPLETED,
}

def _normalize_status(jira_status: str | None) -> Status:
    if not jira_status:
        return Status.TO_DO
    return _JIRA_STATUS_MAP.get(jira_status.lower(), Status.TO_DO)

# ------------------------------------------------------------------
# Issue implementation
# ------------------------------------------------------------------
class JiraIssue(Issue):  # type: ignore[misc]
    """Concrete Issue backed by a Jira issue API response.

    Construct via the module-level ``get_issue()`` factory rather than
    instantiating directly.

    Args:
        issue_id:  The Jira issue key (e.g. 'PROJ-42').
        raw_data: The ``fields``-level dict from the Jira REST API response.
        base_url: The base URL of the Jira instance (e.g. 'https://myorg.atlassian.net').
        client:   Optional JiraClient reference.  When provided, ``update()``
                  delegates mutations back to the client.  When absent,
                  ``update()`` raises ``NotImplementedError``.

    """

    def __init__(
        self,
        issue_id: str,
        raw_data: dict[str, Any],
        base_url: str,
        *,
        client: JiraClient | None = None,
    ) -> None:
        """Initialize JiraIssue."""
        self._id = issue_id
        self._raw = raw_data
        self._base_url = base_url.rstrip("/")
        self._client = client

    @property
    def id(self) -> str:
        """Return id."""
        return self._id

    @property
    def title(self) -> str:
        """Return title."""
        # Jira calls "title" a "summary"
        return str(self._raw.get("summary", ""))
        # Need to cast the string as a string so that mypy believes that the string strings.

    @property
    def desc(self) -> str:
        """Extract description from ADF format."""
        # Jira Cloud returns description as Atlassian Document Format (ADF).
        # So description must be extracted from adf format
        desc = self._raw.get("description")
        if desc is None:
            return ""
        if isinstance(desc, str):
            return desc
        # ADF object → flatten text nodes
        return _extract_adf_text(desc)

    @property
    def description(self) -> str:
        """Backward-compatible alias for desc."""
        return self.desc

    @property
    def status(self) -> Status:
        """Return status."""
        status_name: str = self._raw.get("status", {}).get("name", "") if isinstance(self._raw.get("status"), dict) else ""
        return _normalize_status(status_name)

    @property
    def members(self) -> list[str] | None:
        """Return the assigned members."""
        assignee = self._raw.get("assignee")
        if not assignee:
            return None
        # Prefer email, fall back to displayName
        primary = assignee.get("emailAddress") or assignee.get("displayName") or None
        return [primary] if primary else None

    @property
    def assignee(self) -> str | None:
        """Backward-compatible alias for the primary member."""
        members = self.members
        return members[0] if members else None

    @property
    def board_id(self) -> str:
        """Return the associated board identifier when available."""
        project = self._raw.get("project")
        if isinstance(project, dict):
            return str(project.get("id") or project.get("key") or "")
        return ""

    @property
    def due_date(self) -> str | None:
        """Return due date."""
        return self._raw.get("duedate") or None

    def update(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status | None = None,
        board_id: str | None = None,
    ) -> None:
        """Apply a partial update to this issue via the Jira API.

        Delegates to ``JiraClient.update_issue()``.  Requires that this
        instance was constructed with a ``client`` reference (which happens
        automatically when issues are fetched via ``JiraClient``).

        Args:
            title: Updated title.
            desc: Updated description.
            members: Updated members.
            due_date: Updated due date.
            status: Updated status.
            board_id: Updated board identifier.

        Raises:
            NotImplementedError: If this issue was constructed without a
                                  client reference.

        """
        if self._client is None:
            msg = "This JiraIssue has no client reference; call JiraClient.update_issue() directly."
            raise NotImplementedError(msg)
        self._client.update_issue(
            self._id,
            title=title,
            desc=desc,
            members=members,
            due_date=due_date,
            status=status,
            board_id=board_id,
        )

# ---------------------------------------------------------------------------
# Extract data from ADF format which Jira stores description in
# ---------------------------------------------------------------------------

def _extract_adf_text(node: dict[str, Any]) -> str:
    """Recursively extract plain text from an ADF document node."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return str(node.get("text", ""))
    parts = [_extract_adf_text(child) for child in node.get("content") or []]
    return "\n".join(filter(None, parts))

# ---------------------------------------------------------------------------
# Get issue
# ---------------------------------------------------------------------------

def get_issue(
    issue_id: str,
    raw_data: dict[str, Any],
    base_url: str = "",
    *,
    client: JiraClient | None = None,
) -> JiraIssue:
    """Return a JiraIssue from a Jira REST API issue response.

    Args:
        issue_id:  The Jira issue key (e.g. 'PROJ-42').
        raw_data: The ``fields`` dict from the Jira issue payload.
        base_url: The Jira instance base URL (e.g. 'https://myorg.atlassian.net').
        client:   Optional JiraClient for enabling ``Issue.update()``.

    Returns:
        A JiraIssue instance conforming to the Issue contract.

    """
    return JiraIssue(issue_id, raw_data, base_url, client=client)
