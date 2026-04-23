"""Jira Client implementation.

Authentication
--------------
The client supports two credential modes:

1. API Token (Basic Auth) — get_client(interactive=False) or get_client(interactive=True)
        JIRA_BASE_URL   https://myorg.atlassian.net
        JIRA_USER_EMAIL me@example.com
        JIRA_API_TOKEN  <token from https://id.atlassian.com/manage-profile/security/api-tokens>

2. OAuth2 Bearer Token — get_oauth_client(access_token)
        JIRA_CLOUD_ID   <cloud ID from https://api.atlassian.com/oauth/token/accessible-resources>
        access_token    Atlassian OAuth2 access token (passed at call-time, NOT read from env)

   When using OAuth2, the Atlassian REST API base URL changes to:
        https://api.atlassian.com/ex/jira/{cloud_id}

Dependencies:
    uv add requests

"""

# to avoid having to consider forward declarations, the below line must be first line in the file
from __future__ import annotations

import os
import re
from getpass import getpass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Never, TypeAlias, cast

import requests
from api.issue import Status
from requests.auth import HTTPBasicAuth

from jira_client_impl.jira_board import JiraBoard
from jira_client_impl.jira_issue import JiraIssue
from jira_client_impl.jira_issue import get_issue as _make_issue

if TYPE_CHECKING:
    from collections.abc import Iterator

# A precise definition of what JSON can actually contain!
JsonData: TypeAlias = dict[str, "JsonData"] | list["JsonData"] | str | int | float | bool | None  # noqa: UP040

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_STATUS_TO_JQL: dict[Status, str] = {
    Status.TO_DO: '"To Do"',
    Status.IN_PROGRESS: '"In Progress"',
    Status.COMPLETED: '"Complete"',
}

JIRA_SPECIAL_CHARS = r'(["\'*?=~><!\+\-:&|()\[\]{}\\^])'

# Jira requires a transition to be selected to change status
# the below is a mapping of common statuses and a mapping to a recognized transition in Jira
_STATUS_TO_JIRA_TRANSITION: dict[Status, list[str]] = {
    Status.TO_DO: [
        "to do",
        "reopen issue",
        "reopen",
        "stop progress",
        "backlog",
    ],
    Status.IN_PROGRESS: [
        "in progress",
        "start progress",
        "in development",
        "start development",
        "in work",
    ],
    Status.COMPLETED: [
        "done",
        "resolve issue",
        "close issue",
        "resolved",
        "complete",
        "closed",
    ],
}


class JiraError(Exception):
    """Raise when the Jira API returns an unexpected response."""


class BaseIssueNotFoundError(Exception):
    """Base exception raised when a Jira issue cannot be found."""


class IssueNotFoundError(BaseIssueNotFoundError):
    """Raise when a requested Jira issue does not exist."""


def sanitize_input(value: str) -> str:
    """Sanitize input."""
    return re.sub(JIRA_SPECIAL_CHARS, r"\\\1", value)


def _primary_member(members: list[str] | None) -> str | None:
    """Return the primary member used for Jira's single-assignee model."""
    if not members:
        return None
    return members[0]


# ---------------------------------------------------------------------------
# Client implementation
# ---------------------------------------------------------------------------


class JiraClient:
    """Concrete implementation of the Client abstraction using Jira API.

    Args:
    base_url:   Jira instance root URL (e.g. 'https://myorg.atlassian.net')
    user_email: Email associated with the Jira
    api_token:  API token generated from Atlassian account settings

    """

    _API_PREFIX = "/rest/api/3"
    _AGILE_PREFIX = "/rest/agile/1.0"

    def __init__(
        self,
        base_url: str,
        user_email: str = "",
        api_token: str = "",
        *,
        access_token: str = "",
    ) -> None:
        """Initialize Jira Client.

        Either (user_email + api_token) for Basic Auth, or access_token for OAuth2 Bearer.
        OAuth2 mode is used when the service receives a per-user Atlassian token from the
        Authorization Code flow; in that case base_url should be the Atlassian API base
        (https://api.atlassian.com/ex/jira/{cloud_id}).
        """
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        if access_token:
            # OAuth2 bearer token mode — used by the FastAPI service per-user path
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        else:
            # API token / Basic Auth mode — used by the local library path
            self._auth = HTTPBasicAuth(user_email, api_token)
            self._session.auth = self._auth
            self._session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Return base url."""
        return f"{self._base_url}{self._API_PREFIX}{path}"

    def _agile_url(self, path: str) -> str:
        """Return agile API url (used for board and sprint endpoints)."""
        return f"{self._base_url}{self._AGILE_PREFIX}{path}"

    def _agile_get(self, path: str, params: dict[str, Any] | None = None) -> JsonData:
        """Perform a GET against the Jira Agile REST API."""
        response = self._session.get(self._agile_url(path), params=params)
        self._raise_for_status(response)
        return cast("JsonData", response.json())

    def _get(self, path: str, params: dict[str, Any] | None = None) -> JsonData:
        """Return json response for HTTP get message."""
        response = self._session.get(self._url(path), params=params)
        self._raise_for_status(response)
        return cast("JsonData", response.json())

    def _post(self, path: str, body: dict[str, Any]) -> JsonData:
        """Send HTTP Post message and return response."""
        response = self._session.post(self._url(path), json=body)
        self._raise_for_status(response)
        return cast("JsonData", response.json())

    def _put(self, path: str, body: dict[str, Any]) -> JsonData:
        """Perform put operation."""
        response = self._session.put(self._url(path), json=body)
        self._raise_for_status(response)
        # Jira PUT /issue returns 204 No Content on success
        if response.status_code == HTTPStatus.NO_CONTENT:
            return {}
        return cast("JsonData", response.json())

    def _delete(self, path: str) -> bool:
        """Perform deletion."""
        response = self._session.delete(self._url(path))
        if response.status_code == HTTPStatus.NOT_FOUND:
            return False
        self._raise_for_status(response)
        return True

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        """Raise appropiate error."""
        if response.status_code == HTTPStatus.NOT_FOUND:
            msg = f"Resource not found: {response.url}"
            raise IssueNotFoundError(msg)
        if not response.ok:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            msg = f"Jira API error {response.status_code}: {detail}"
            raise JiraError(msg)

    def build_issue(self, issue: dict[str, Any]) -> JiraIssue:
        """Build Jira Issue."""
        return _make_issue(issue["key"], issue.get("fields", {}), self._base_url, client=self)

    def _build_jql_query(
        self,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
    ) -> str:
        """Construct a JQL query string based on provided filters."""
        clauses: list[str] = []

        if title:
            clean_title = sanitize_input(title)
            # summary is Jira's term for "title"
            clauses.append(f"summary ~ '{clean_title}'")
        if desc:
            clean_description = sanitize_input(desc)
            clauses.append(f"description ~ '{clean_description}'")
        if status:
            # value comes from an internal hardcoded map, not user input, so no sanitization needed
            clauses.append(f"status = {_STATUS_TO_JQL[status]}")
        if due_date:
            clean_due_date = sanitize_input(due_date)
            clauses.append(f"due = '{clean_due_date}'")
        primary_member = _primary_member(members)
        if primary_member:
            clean_assignee = sanitize_input(primary_member)
            clauses.append(f"assignee = '{clean_assignee}'")

        # build JQL query
        # Jira requires a bounding clause for queries. Adding this dummy bound bypasses that requirement
        if not clauses:
            clauses.append("project IS NOT EMPTY")

        return " AND ".join(clauses) + " ORDER BY updated DESC"

    # ------------------------------------------------------------------
    # IssueTrackerClient contract
    # ------------------------------------------------------------------

    def get_issue(self, issue_id: str) -> JiraIssue:
        """Fetch a single Jira issue by id."""
        # _get returns a json string, build_issue builds the Issue instance
        data = self._get(f"/issue/{issue_id}")

        if not isinstance(data, dict):
            msg = f"Jira API returned {type(data)} for issue {issue_id}, expected dict"
            raise TypeError(msg)
        return self.build_issue(data)

    def get_issues(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        max_results: int = 20,
    ) -> Iterator[JiraIssue]:
        """Get issues.

        Iteration stops once "max_results" number of issues have been yielded or no more results exist.
        """
        # 1. Delegate the complex JQL string building to our new helper method
        jql = self._build_jql_query(
            title=title,
            desc=desc,
            status=status,
            members=members,
            due_date=due_date,
        )

        start_at = 0
        page_size = min(max_results, 100)  # Jira's maximum is 100
        yielded = 0

        # 2. Each iteration makes one API request, fetching the next page
        # Stop requesting pages when we have passed the total number of issues Jira reported
        while yielded < max_results:
            data = self._get(
                "/search/jql",
                params={"jql": jql, "startAt": start_at, "maxResults": page_size, "fields": "*all"},
            )

            if not isinstance(data, dict):
                break

            raw_issues = data.get("issues")
            total = data.get("total", 0)

            if not isinstance(raw_issues, list):
                break

            issues: list[dict[str, Any]] = [i for i in raw_issues if isinstance(i, dict)]

            if not issues:
                break

            # Builds issue and increments yield count until max_results is met
            for issue in issues:
                if yielded >= max_results:
                    return
                yield self.build_issue(issue)
                yielded += 1

            start_at += len(issues)
            if isinstance(total, int) and start_at >= total:
                break

    def create_issue(
        self,
        *,
        title: str | None = None,
        desc: str | None = None,
        status: Status | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        board_id: str | None = None,
    ) -> JiraIssue:
        # A board is a required field in Jira, and likely all other issue tracker implementations
        """Create a new Jira issue and return it as a JiraIssue."""
        # Use board_id as project key if provided, otherwise use OPS as default
        project_key = board_id or "OPS"

        # required fields -- title, issue type, and project
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": title,
            "issuetype": {"name": "Task"},
        }
        if desc:
            # Jira Cloud expects Atlassian Document Format for description
            fields["description"] = _text_to_adf(desc)
        primary_member = _primary_member(members)
        if primary_member:
            fields["assignee"] = {"emailAddress": primary_member}
        if due_date:
            fields["duedate"] = due_date
        data = self._post("/issue", {"fields": fields})

        if not isinstance(data, dict):
            msg = "Excpected dict from Jira API"
            raise TypeError(msg)

        issue_key = str(data.get("key", ""))

        # Jira doesn't allow setting status directly, must go through the Transitions API
        # So it needs its own dedicated call
        # Status is set after the issue is created in Jira
        if status:
            self._apply_status_transition(issue_key, status)

        return self.get_issue(issue_key)

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status | None = None,
        board_id: str | None = None,  # noqa: ARG002
    ) -> JiraIssue:
        """Update issue.

        Args:
            issue_id: The Jira issue id
            title: Updated title.
            desc: Updated description.
            members: Updated members list.
            due_date: Updated due date.
            status: Updated status.
            board_id: Updated board identifier.

        Notes on usage:
            Applies a partial update to an existing Jira issue and return the updated issue.
            Fields left as "None" are not sent to the API and remain unchanged.
            Status changes are handled via the Jira Transitions API because Jira does not allow direct status field edits

        Returns:
            The updated JiraIssue

        Raises:
            IssueNotFoundError: If the issue does not exist.
            JiraError: If a requested status transition is unavailable.

        """
        fields: dict[str, Any] = {}
        if title is not None:
            fields["summary"] = title
        if desc is not None:
            fields["description"] = _text_to_adf(desc)
        if members is not None:
            primary_member = _primary_member(members)
            fields["assignee"] = {"emailAddress": primary_member} if primary_member else None
        if due_date is not None:
            fields["duedate"] = due_date
        if fields:
            self._put(f"/issue/{issue_id}", {"fields": fields})

        # status changes must occur after the _put call
        if status is not None:
            self._apply_status_transition(issue_id, status)

        return self.get_issue(issue_id)

    def delete_issue(self, issue_id: str) -> None:
        """Delete a Jira issue, and will raise error if issue is not found.

        Raises:
            IssueNotFoundError: If no issue with that ID exists.

        """
        self._delete(f"/issue/{issue_id}")

    # ------------------------------------------------------------------
    # Board access (Jira Agile API)
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> JiraBoard:
        """Return a single Jira board by id.

        Args:
            board_id: The Jira agile board ID.

        Returns:
            A JiraBoard instance.

        Raises:
            IssueNotFoundError: If no board with that ID exists.

        """
        data = self._agile_get(f"/board/{board_id}")
        if not isinstance(data, dict):
            msg = f"Jira API returned unexpected type for board {board_id}"
            raise TypeError(msg)
        return JiraBoard(
            _board_id=str(board_id),
            _name=str(data.get("name", "")),
            _client=self,
        )

    def get_boards(self) -> Iterator[JiraBoard]:
        """Return an iterator over all Jira agile boards visible to the current credentials.

        Yields:
            JiraBoard instances, one per board.

        """
        start_at = 0
        page_size = 50
        while True:
            data = self._agile_get("/board", params={"startAt": start_at, "maxResults": page_size})
            if not isinstance(data, dict):
                break
            values = data.get("values", [])
            if not isinstance(values, list) or not values:
                break
            for board in values:
                if not isinstance(board, dict):
                    continue
                yield JiraBoard(
                    _board_id=str(board.get("id", "")),
                    _name=str(board.get("name", "")),
                    _client=self,
                )
            start_at += len(values)
            if data.get("isLast", True):
                break

    # ------------------------------------------------------------------
    # List access (board columns exposed as List objects)
    # ------------------------------------------------------------------

    def get_list(self, list_id: str) -> Never:
        """List access is not currently supported in this checkout."""
        raise NotImplementedError

    def get_lists(self, board_id: str) -> Iterator[Any]:
        """List access is not currently supported in this checkout."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Status transition helper
    # ------------------------------------------------------------------

    def _apply_status_transition(self, issue_id: str, target: Status) -> None:
        """Transition are named actions in Jira that move one Issue from one status to another.

        You have to ask Jira which transitions are available for specific issue, and then trigger
        said transition by its ID.
        """
        # since our status value have an undercore, this changes the underscores to spaces, and lowers text
        target.value.replace("_", " ").lower()

        # calls the Jira API to get a list of transitions available for this issue
        data = self._get(f"/issue/{issue_id}/transitions")

        if not isinstance(data, dict):
            msg = "Expected dict from Jira API"
            raise TypeError(msg)

        raw_transitions = data.get("transitions", [])

        if not isinstance(raw_transitions, list):
            raw_transitions = []

        transitions: list[dict[str, Any]] = [t for t in raw_transitions if isinstance(t, dict)]

        # build a lookup of available transition names -> transition object
        available = {t.get("name", "").lower(): t for t in transitions}

        # Find a transition from the given common Status-to-Transition map whose name contains the target status keyword
        match = None
        for candidate in _STATUS_TO_JIRA_TRANSITION[target]:
            if candidate.lower() in available:
                match = available[candidate.lower()]
                break
        # raises Jira error if there are no available transitions
        if match is None:
            msg = f"No transition to '{target.value}' found for {issue_id}. Available transitions: {list(available.keys())}"
            raise JiraError(msg)

        self._post(f"/issue/{issue_id}/transitions", {"transition": {"id": match["id"]}})


# ---------------------------------------------------------------------------
# ADF builder -  Jira requires description data to be in this format
# ---------------------------------------------------------------------------


def _text_to_adf(text: str) -> dict[str, Any]:
    """Translate text to adf format.

    Notes on usage:
    Jira Cloud requires that certain fields, particularly description, are sent to the API in Atlassian Document Format (ADF),
    otherwise it will be rejected
    """
    if not isinstance(text, str):
        msg = "Input must be a string"
        raise JiraError(msg)
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Get client
# ---------------------------------------------------------------------------


def get_client(*, interactive: bool = False) -> JiraClient:
    """Return a configured JiraClient.

    Reads credentials from environment variables. If "interactive = True" and
    any variable is missing, the user will be prompted.

    Environment variables:
        JIRA_BASE_URL:    Base URL of the Jira instance.
        JIRA_USER_EMAIL:  Atlassian account email.
        JIRA_API_TOKEN:   API token from Atlassian account settings.
    """
    base_url = os.environ.get("JIRA_BASE_URL", "")
    user_email = os.environ.get("JIRA_USER_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    # This if block is not included in test coverage calculations, because it is meant for development purposes only.
    if interactive:  # pragma: no cover
        if not base_url:
            base_url = input("Jira base URL (e.g. https://myorg.atlassian.net): ").strip()
        if not user_email:
            user_email = input("Jira user email: ").strip()
        if not api_token:
            api_token = getpass("Jira API token: ")
    else:
        # collects the missing fields and raises an error alerting to the missing values
        missing = [
            name
            for name, val in [
                ("JIRA_BASE_URL", base_url),
                ("JIRA_USER_EMAIL", user_email),
                ("JIRA_API_TOKEN", api_token),
            ]
            if not val
        ]
        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}. Set them or call get_client(interactive=True)."
            raise OSError(msg)

    return JiraClient(base_url, user_email, api_token)


def get_oauth_client(access_token: str) -> JiraClient:
    """Return a JiraClient configured for OAuth2 Bearer token authentication.

    This is the correct factory to use inside the FastAPI service when the caller
    has already completed the OAuth2 Authorization Code flow and holds a per-user
    Atlassian access token.

    The Atlassian REST API for OAuth2 apps uses a different base URL:
        https://api.atlassian.com/ex/jira/{cloud_id}

    Environment variables:
        JIRA_CLOUD_ID: The cloud ID from
            https://api.atlassian.com/oauth/token/accessible-resources

    Args:
        access_token: A valid Atlassian OAuth2 access token.

    Raises:
        OSError: If JIRA_CLOUD_ID environment variable is not set.

    """
    cloud_id = os.environ.get("JIRA_CLOUD_ID", "")
    if not cloud_id:
        msg = (
            "Missing required environment variable: JIRA_CLOUD_ID. "
            "Set it to the cloud ID from https://api.atlassian.com/oauth/token/accessible-resources"
        )
        raise OSError(msg)
    base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"
    return JiraClient(base_url, access_token=access_token)
