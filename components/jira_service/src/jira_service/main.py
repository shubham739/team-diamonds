"""FastAPI server with Jira OAuth2 authentication and work management endpoints."""

import logging
import os
import secrets
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel

from jira_client_impl import get_client, get_oauth_client
from jira_client_impl.jira_impl import IssueNotFoundError as BaseIssueNotFoundError
from jira_service.auth import (
    AuthenticationError,
    exchange_code_for_token,
    get_authorize_url,
    get_user_info,
    get_valid_token,
    store_session,
    user_sessions,
)
from jira_service.exceptions import ClientInitializationError
from api.issue import Status

IssueTrackerClient = Any

# Loading .env from inside .venv for local development
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

# FastAPI instance
app = FastAPI(
    title="Jira Service API",
    description="OAuth2-authenticated Jira work management API",
    # Use the default Swagger OAuth2 redirect path so it does not conflict
    # with our custom /auth/callback endpoint.
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": os.getenv("JIRA_OAUTH_CLIENT_ID"),
        "scopes": "read:me read:jira-work write:jira-work offline_access",
        "usePkceWithAuthorizationCodeGrant": False,
    },
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://auth.atlassian.com/authorize",
    tokenUrl="https://auth.atlassian.com/oauth/token",
)

# CSRF state store (in-memory; lives for the duration of one auth round-trip)
auth_states: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Pydantic request models — mutations use JSON body, not query params
# ---------------------------------------------------------------------------


class CreateIssueRequest(BaseModel):
    """Request body for creating a new issue."""

    title: str | None = None
    desc: str | None = None
    status: Status | None = None
    members: list[str] | None = None
    due_date: str | None = None
    board_id: str | None = None


class UpdateIssueRequest(BaseModel):
    """Request body for updating an existing issue."""

    title: str | None = None
    desc: str | None = None
    status: Status | None = None
    members: list[str] | None = None
    due_date: str | None = None
    board_id: str | None = None


# ---------------------------------------------------------------------------
# Dependency Injection: Client Factory
# ---------------------------------------------------------------------------


def get_jira_client(token: Annotated[str, Depends(oauth2_scheme)]) -> IssueTrackerClient:
    """FastAPI dependency that provides a per-request, per-user JiraClient.

    Strategy (tried in order):
    1. If JIRA_CLOUD_ID is set, use the OAuth2 bearer token the user obtained
       from the Atlassian Authorization Code flow. This is the multi-user path.
    2. Fall back to Basic Auth with JIRA_USER_EMAIL / JIRA_API_TOKEN. This
       is the single-developer / API-token path and is also used when the
       Bearer token passed to the endpoint is not a user session token but
       rather a service-level API token.

    Raises:
        HTTPException 503: If neither credential set is available.

    """
    # --- Try OAuth2 bearer path first (multi-user, production path) ---
    cloud_id = os.environ.get("JIRA_CLOUD_ID", "")
    if cloud_id:
        # The token in the Authorization header is the user's Atlassian access
        # token obtained from the OAuth2 callback.  We also auto-refresh via
        # the session store if the caller passes us their user_id as a header;
        # but for simplicity the bearer token itself is always authoritative.
        try:
            return get_oauth_client(token)
        except OSError as e:
            raise HTTPException(
                status_code=503,
                detail="Jira OAuth2 client not configured: check JIRA_CLOUD_ID",
            ) from e

    # --- Fall back to API token / Basic Auth path (single-user / dev path) ---
    try:
        return get_client(interactive=False)
    except OSError as e:
        raise HTTPException(
            status_code=503,
            detail="Jira client not configured: set JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN",
        ) from e


# ---------------------------------------------------------------------------
# Health and Auth Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint. Returns 200 OK regardless of Jira connectivity."""
    try:
        _ = get_client(interactive=False)
        logger.info("Health check passed — Jira Basic Auth client available")
    except OSError:
        logger.warning("Health check: Jira Basic Auth client not configured (OAuth2 may still work)")
    return {"status": "ok"}


@app.get("/auth/login")
def login() -> RedirectResponse:
    """Initiate OAuth2 Authorization Code flow by redirecting to Atlassian."""
    state = secrets.token_urlsafe(32)
    auth_states[state] = state
    auth_url = get_authorize_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
def callback(
    authorization_code: Annotated[str, Query(alias="code")],
    csrf_state: Annotated[str, Query(alias="state")],
) -> dict[str, str | None]:
    """OAuth2 callback endpoint.

    Validates the CSRF state, exchanges the authorization code for tokens,
    fetches the user's Atlassian account info, and stores the session.

    Args:
        authorization_code: OAuth authorization code from Atlassian.
        csrf_state: CSRF state token (must match one issued by /auth/login).

    Returns:
        Authentication result with user_id, email, name, and access_token.

    Raises:
        HTTPException 400: If state is invalid or token exchange fails.

    """
    if csrf_state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter") from None

    try:
        token_data = exchange_code_for_token(authorization_code)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token") from e

    access_token: str = token_data.get("access_token", "")

    try:
        user_info = get_user_info(access_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail="Failed to get user info") from e

    user_id: str = user_info.get("account_id", "")
    store_session(user_id, token_data)
    del auth_states[csrf_state]

    # Return the access token so the caller can use it in subsequent Bearer requests.
    return {
        "status": "authenticated",
        "user_id": user_id,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "access_token": access_token,
    }


@app.get("/auth/logout")
def logout(user_id: Annotated[str | None, Query()] = None) -> dict[str, str]:
    """Clear user session and log out.

    Args:
        user_id: User identifier (optional; no-op if not supplied or not found).

    Returns:
        Logout confirmation.

    """
    if user_id and user_id in user_sessions:
        del user_sessions[user_id]
        logger.info("User %s logged out", user_id)
    return {"status": "logged out"}


# ---------------------------------------------------------------------------
# Shared response helper
# ---------------------------------------------------------------------------


def _issue_to_dict(issue: Any) -> dict[str, Any]:  # noqa: ANN401
    """Serialize an Issue instance to a plain dict for JSON responses."""
    return {
        "id": issue.id,
        "title": issue.title,
        "desc": issue.desc,
        "status": str(issue.status),
        "members": issue.members,
        "due_date": issue.due_date,
    }


# ---------------------------------------------------------------------------
# Issue CRUD Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root(
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
) -> dict[str, Any]:
    """Fetch the 5 most recently updated Jira issues.

    Args:
        client: Jira client instance (injected, per-user OAuth2 or Basic Auth).

    Returns:
        Dictionary with ``issues`` list.

    Raises:
        HTTPException 500: On unexpected errors.

    """
    try:
        issues = [_issue_to_dict(issue) for issue in client.get_issues(max_results=5)]
    except ClientInitializationError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error fetching issues")
        raise HTTPException(status_code=500, detail="Unexpected error while fetching issues") from e
    return {"issues": issues}


@app.get("/issues/{issue_id}")
def get_issue(
    issue_id: str,
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
) -> dict[str, Any]:
    """Get a single issue by ID.

    Args:
        issue_id: Jira issue key (e.g. ``PROJ-42``).
        client: Jira client instance (injected).

    Returns:
        Issue data dictionary.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 500: On unexpected errors.

    """
    try:
        return _issue_to_dict(client.get_issue(issue_id))
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except Exception as e:
        logger.exception("Error fetching issue %s", issue_id)
        raise HTTPException(status_code=500, detail="Unexpected error while fetching the issue") from e


@app.get("/issues")
def list_issues(
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
    title: Annotated[str | None, Query()] = None,
    desc: Annotated[str | None, Query()] = None,
    status: Annotated[Status | None, Query()] = None,
    members: Annotated[list[str] | None, Query()] = None,
    due_date: Annotated[str | None, Query()] = None,
    max_results: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """List issues with optional filters.

    Args:
        client: Jira client instance (injected).
        title: Filter by title substring.
        desc: Filter by description substring.
        status: Filter by status.
        members: Filter by member email.
        due_date: Filter by due date (YYYY-MM-DD).
        max_results: Maximum number of results to return (1–100).

    Returns:
        Dictionary with ``issues`` list and ``count``.

    Raises:
        HTTPException 422: On invalid query parameters.
        HTTPException 500: On unexpected errors.

    """
    try:
        issues = [
            _issue_to_dict(issue)
            for issue in client.get_issues(
                title=title,
                desc=desc,
                status=status,
                members=members,
                due_date=due_date,
                max_results=max_results,
            )
        ]
        return {"issues": issues, "count": len(issues)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid query parameters: {e!s}") from e
    except Exception as e:
        logger.exception("Error listing issues")
        raise HTTPException(status_code=500, detail="Unexpected error while listing issues") from e


@app.post("/issues", status_code=201)
def create_issue(
    body: CreateIssueRequest,
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
) -> dict[str, Any]:
    """Create a new issue.

    The request body (JSON) maps to the fields of a new Jira issue.

    Args:
        body: Issue fields (title, desc, status, members, due_date, board_id).
        client: Jira client instance (injected).

    Returns:
        Created issue data with HTTP 201.

    Raises:
        HTTPException 422: On invalid issue data.
        HTTPException 500: On unexpected errors.

    """
    try:
        issue = client.create_issue(
            title=body.title,
            desc=body.desc,
            status=body.status,
            members=body.members,
            due_date=body.due_date,
            board_id=body.board_id,
        )
        logger.info("Created issue %s", issue.id)
        return _issue_to_dict(issue)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid issue data: {e!s}") from e
    except Exception as e:
        logger.exception("Error creating issue")
        raise HTTPException(status_code=500, detail="Unexpected error while creating the issue") from e


@app.put("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    body: UpdateIssueRequest,
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
) -> dict[str, Any]:
    """Update an existing issue.

    Only the fields present in the JSON body are updated; omitted fields are
    left unchanged.

    Args:
        issue_id: Jira issue key.
        body: Fields to update.
        client: Jira client instance (injected).

    Returns:
        Updated issue data.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 422: On invalid update data.
        HTTPException 500: On unexpected errors.

    """
    try:
        issue = client.update_issue(
            issue_id,
            title=body.title,
            desc=body.desc,
            status=body.status,
            members=body.members,
            due_date=body.due_date,
            board_id=body.board_id,
        )
        logger.info("Updated issue %s", issue_id)
        return _issue_to_dict(issue)
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid update data: {e!s}") from e
    except Exception as e:
        logger.exception("Error updating issue %s", issue_id)
        raise HTTPException(status_code=500, detail="Unexpected error while updating the issue") from e


@app.delete("/issues/{issue_id}", status_code=200)
def delete_issue(
    issue_id: str,
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
) -> dict[str, str]:
    """Delete an issue.

    Args:
        issue_id: Jira issue key.
        client: Jira client instance (injected).

    Returns:
        Deletion confirmation.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 500: On unexpected errors.

    """
    try:
        client.delete_issue(issue_id)
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except Exception as e:
        logger.exception("Error deleting issue %s", issue_id)
        raise HTTPException(status_code=500, detail="Unexpected error while deleting the issue") from e
    logger.info("Deleted issue %s", issue_id)
    return {"status": "deleted", "issue_id": issue_id}
