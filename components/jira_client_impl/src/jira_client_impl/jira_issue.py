"""Jira Issue implementation."""

from work_mgmt_client_interface.issue import Issue, Status

# ---------------------------------------------------------------------------
# Mapping tables: Jira-native values  →  normalized enum values
# ---------------------------------------------------------------------------

#to clean user's input into a standardized status that is used across all implementations
_JIRA_STATUS_MAP: dict[str, Status] = {
    #to do
    "to do":        Status.TODO,
    "open":         Status.TODO,
    "backlog":      Status.TODO,
    "new":          Status.TODO,

    #in progress
    "in progress":  Status.IN_PROGRESS,
    "working":      Status.IN_PROGRESS,
    "development":  Status.IN_PROGRESS,

    #done
    "complete":     Status.COMPLETE,
    "done":         Status.COMPLETE,
    "closed":       Status.COMPLETE,
    "resolved":     Status.COMPLETE,

    #cancelled
    "cancelled":    Status.CANCELLED,
    "canceled":     Status.CANCELLED,
    "rejected":     Status.CANCELLED,
}

def _normalize_status(jira_status: str | None) -> Status:
    if not jira_status:
        return Status.TODO
    return _JIRA_STATUS_MAP.get(jira_status.lower(), Status.TODO)

# ------------------------------------------------------------------
# Issue implementation
# ------------------------------------------------------------------
class JiraIssue(Issue):
    """Concrete Issue backed by a Jira issue API response.

    Construct via the module-level ``get_issue()`` factory rather than
    instantiating directly.

    Args:
        issue_id:  The Jira issue key (e.g. 'PROJ-42').
        raw_data: The ``fields``-level dict from the Jira REST API response.
        base_url: The base URL of the Jira instance (e.g. 'https://myorg.atlassian.net').

    """

    def __init__(self, issue_id: str, raw_data: dict, base_url: str) -> None:
        """Initialize JiraIssue."""
        self._id = issue_id
        self._raw = raw_data
        self._base_url = base_url.rstrip("/")

    @property
    def id(self) -> str:
        """Return id."""
        return self._id

    @property
    def title(self) -> str:
        """Return title."""
        #Jira calls "title" a "summary"
        return self._raw.get("summary", "")

    @property
    def description(self) -> str:
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
    def status(self) -> Status:
        """Return status."""
        status_name: str = (
            self._raw.get("status", {}).get("name", "") if isinstance(self._raw.get("status"), dict) else ""
        )
        return _normalize_status(status_name)

    @property
    def assignee(self) -> str | None:
        """Return name to task assignee."""
        assignee = self._raw.get("assignee")
        if not assignee:
            return None
        # Prefer email, fall back to displayName
        return assignee.get("emailAddress") or assignee.get("displayName") or None

    @property
    def due_date(self) -> str | None:
        """Return due date."""
        return self._raw.get("duedate") or None


# ---------------------------------------------------------------------------
# Extract data from ADF format which Jira stores description in
# ---------------------------------------------------------------------------

def _extract_adf_text(node: dict) -> str:
    """Recursively extract plain text from an ADF document node."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_extract_adf_text(child) for child in node.get("content") or []]
    return "\n".join(filter(None, parts))


# ---------------------------------------------------------------------------
# Get issue
# ---------------------------------------------------------------------------

def get_issue(issue_id: str, raw_data: dict, base_url: str = "") -> JiraIssue:
    """Return a JiraIssue from a Jira REST API issue response.

    Args:
        issue_id:  The Jira issue key (e.g. 'PROJ-42').
        raw_data: The ``fields`` dict from the Jira issue payload.
        base_url: The Jira instance base URL (e.g. 'https://myorg.atlassian.net').

    Returns:
        A JiraIssue instance conforming to the Issue contract.

    """
    return JiraIssue(issue_id, raw_data, base_url)
