"""FastAPI server with Jira OAuth2 authentication and work management endpoints."""

import logging
import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Loading .env from inside .venv
venv_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".venv", ".env")
load_dotenv(venv_env_path)

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse
from jira_client_impl import get_client
from work_mgmt_client_interface.client import IssueNotFoundError as BaseIssueNotFoundError
from work_mgmt_client_interface.issue import Status, IssueUpdate

from jira_service.auth import (
    get_authorize_url,
    exchange_code_for_token,
    get_user_info,
    store_session,
    get_valid_token,
    user_sessions,
    AuthenticationError,
    TokenRefreshError,
)
from jira_service.exceptions import (
    IssueNotFoundError,
    IssueOperationError,
    ClientInitializationError,
)

logger = logging.getLogger(__name__)

# FastAPI instance
app = FastAPI(
    title="Jira Service API",
    description="OAuth2-authenticated Jira work management API",
    swagger_ui_oauth2_redirect_url="/auth/callback",
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

auth_states: dict[str, str] = {}

# -----------------------------------------------------------------------
# Dependency Injection: Client Factory
# -----------------------------------------------------------------------


def get_jira_client():
    """FastAPI dependency to provide a Jira client instance.

    Yields:
        JiraClient instance

    Raises:
        ClientInitializationError: If client cannot be initialized
    """
    try:
        client = get_client(interactive=False)
        yield client
    except OSError as e:
        raise ClientInitializationError(
            "Jira client not configured: check environment variables"
        ) from e


# -----------------------------------------------------------------------
# Health and Auth Endpoints
# -----------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    try:
        client = get_client(interactive=False)
        logger.info("Health check passed")
    except OSError:
        # Return healthy status even if Jira client can't be initialized
        logger.warning("Health check: Jira client not configured")
    return {"status": "ok"}


@app.get("/auth/login")
def login() -> RedirectResponse:
    """Initiate OAuth2 login flow by redirecting to Jira."""
    state = secrets.token_urlsafe(32)
    auth_states[state] = state
    auth_url = get_authorize_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
def callback(
    authorization_code: str = Query(alias="code"),
    csrf_state: str = Query(alias="state"),
) -> dict[str, str | None]:
    """OAuth2 callback endpoint.

    Args:
        authorization_code: OAuth authorization code
        csrf_state: CSRF state token

    Returns:
        Authentication result with user info

    Raises:
        HTTPException: If callback parameters are invalid or exchange fails
    """
    if csrf_state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter") from None

    try:
        token_data = exchange_code_for_token(authorization_code)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=400, detail="Failed to exchange code for token"
        ) from e

    try:
        user_info = get_user_info(token_data.get("access_token", ""))
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail="Failed to get user info") from e

    user_id = user_info.get("account_id")
    store_session(user_id, token_data)
    del auth_states[csrf_state]

    return {
        "status": "authenticated",
        "user_id": user_id,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
    }


@app.get("/auth/logout")
def logout(user_id: str | None = Query(None)) -> dict[str, str]:
    """Clear user session and log out.

    Args:
        user_id: User identifier (optional)

    Returns:
        Logout confirmation
    """
    if user_id and user_id in user_sessions:
        del user_sessions[user_id]
        logger.info("User %s logged out", user_id)
    return {"status": "logged out"}


# -----------------------------------------------------------------------
# Issue CRUD Endpoints
# -----------------------------------------------------------------------


@app.get("/")
def root(token: str = Depends(oauth2_scheme), client=Depends(get_jira_client)) -> dict:
    """Fetch Jira issues via local library.

    Args:
        token: OAuth token (validated by security dependency)
        client: Jira client instance (injected)

    Returns:
        Dictionary with issues list

    Raises:
        HTTPException: If issues cannot be fetched
    """
    try:
        issues = [
            {"id": issue.id, "title": issue.title, "status": str(issue.status)}
            for issue in client.get_issues(max_results=5)
        ]
        return {"issues": issues}
    except ClientInitializationError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("Error fetching issues: %s", str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while fetching issues"
        ) from e


@app.get("/issues/{issue_id}")
def get_issue(
    issue_id: str,
    token: str = Depends(oauth2_scheme),
    client=Depends(get_jira_client),
) -> dict:
    """Get a single issue by ID.

    Args:
        issue_id: Issue identifier
        token: OAuth token
        client: Jira client instance

    Returns:
        Issue data dictionary

    Raises:
        HTTPException: If issue not found or fetch fails
    """
    try:
        issue = client.get_issue(issue_id)
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except Exception as e:
        logger.error("Error fetching issue %s: %s", issue_id, str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while fetching the issue"
        ) from e


@app.get("/issues")
def list_issues(
    token: str = Depends(oauth2_scheme),
    client=Depends(get_jira_client),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """List issues with optional filters.

    Args:
        token: OAuth token
        client: Jira client instance
        title: Filter by title
        description: Filter by description
        status: Filter by status
        assignee: Filter by assignee
        due_date: Filter by due date
        max_results: Maximum results to return

    Returns:
        Dictionary with issues list and count

    Raises:
        HTTPException: If listing fails
    """
    try:
        issues = [
            {
                "id": issue.id,
                "title": issue.title,
                "description": issue.description,
                "status": str(issue.status),
                "assignee": issue.assignee,
                "due_date": issue.due_date,
            }
            for issue in client.get_issues(
                title=title,
                description=description,
                status=status,
                assignee=assignee,
                due_date=due_date,
                max_results=max_results,
            )
        ]
        return {"issues": issues, "count": len(issues)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid query parameters: {str(e)}") from e
    except Exception as e:
        logger.error("Error listing issues: %s", str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while listing issues"
        ) from e


@app.post("/issues")
def create_issue(
    token: str = Depends(oauth2_scheme),
    client=Depends(get_jira_client),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
) -> dict:
    """Create a new issue.

    Args:
        token: OAuth token
        client: Jira client instance
        title: Issue title
        description: Issue description
        status: Initial status
        assignee: Assignee
        due_date: Due date

    Returns:
        Created issue data

    Raises:
        HTTPException: If creation fails
    """
    try:
        issue = client.create_issue(
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
        )
        logger.info("Created issue %s", issue.id)
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid issue data: {str(e)}") from e
    except Exception as e:
        logger.error("Error creating issue: %s", str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while creating the issue"
        ) from e


@app.put("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    token: str = Depends(oauth2_scheme),
    client=Depends(get_jira_client),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
) -> dict:
    """Update an existing issue.

    Args:
        issue_id: Issue identifier
        token: OAuth token
        client: Jira client instance
        title: New title
        description: New description
        status: New status
        assignee: New assignee
        due_date: New due date

    Returns:
        Updated issue data

    Raises:
        HTTPException: If update fails
    """
    try:
        update = IssueUpdate(
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
        )
        issue = client.update_issue(issue_id, update)
        logger.info("Updated issue %s", issue_id)
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid update data: {str(e)}") from e
    except Exception as e:
        logger.error("Error updating issue %s: %s", issue_id, str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while updating the issue"
        ) from e


@app.delete("/issues/{issue_id}")
def delete_issue(
    issue_id: str,
    token: str = Depends(oauth2_scheme),
    client=Depends(get_jira_client),
) -> dict:
    """Delete an issue.

    Args:
        issue_id: Issue identifier
        token: OAuth token
        client: Jira client instance

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If deletion fails
    """
    try:
        client.delete_issue(issue_id)
        logger.info("Deleted issue %s", issue_id)
        return {"status": "deleted", "issue_id": issue_id}
    except BaseIssueNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found") from e
    except Exception as e:
        logger.error("Error deleting issue %s: %s", issue_id, str(e))
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while deleting the issue"
        ) from e
