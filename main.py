"""FastAPI server with Jira OAuth2 authentication and work management endpoints."""

import os
import secrets
from dotenv import load_dotenv

# loading .env from inside .venv
venv_env_path = os.path.join(os.path.dirname(__file__), ".venv", ".env")
load_dotenv(venv_env_path)
from jira_client_impl import get_client
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse
from work_mgmt_client_interface.issue import Status, IssueUpdate

from auth import (
    get_authorize_url,
    exchange_code_for_token,
    get_user_info,
    store_session,
    get_valid_token,
    user_sessions,
)


# Fast API connection to the server
app = FastAPI(
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


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    client = get_client(interactive=False)
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
    if csrf_state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    token_data = exchange_code_for_token(authorization_code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    
    access_token = token_data.get("access_token")
    user_info = get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
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
def logout(user_id: str) -> dict[str, str]:
    """Clear user session and log out."""
    if user_id in user_sessions:
        del user_sessions[user_id]
    return {"status": "logged out"}

@app.get("/")
def root(token: str = Depends(oauth2_scheme)) -> dict:
    """Fetch Jira issues via local library."""
    client = get_client(interactive=False)
    issues = [
        {"id": issue.id, "title": issue.title, "status": str(issue.status)}
        for issue in client.get_issues(max_results=5)
    ]
    return {"issues": issues}


# ------------------------------------------------------------------
# Issue CRUD Endpoints
# ------------------------------------------------------------------

@app.get("/issues/{issue_id}")
def get_issue(issue_id: str, token: str = Depends(oauth2_scheme)) -> dict:
    """Get a single issue by ID."""
    try:
        client = get_client(interactive=False)
        issue = client.get_issue(issue_id)
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Issue not found: {str(e)}")


@app.get("/issues")
def list_issues(
    token: str = Depends(oauth2_scheme),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """List issues with optional filters."""
    try:
        client = get_client(interactive=False)
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching issues: {str(e)}")


@app.post("/issues")
def create_issue(
    token: str = Depends(oauth2_scheme),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
) -> dict:
    """Create a new issue."""
    try:
        client = get_client(interactive=False)
        issue = client.create_issue(
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
        )
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating issue: {str(e)}")


@app.put("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    token: str = Depends(oauth2_scheme),
    title: str | None = Query(None),
    description: str | None = Query(None),
    status: Status | None = Query(None),
    assignee: str | None = Query(None),
    due_date: str | None = Query(None),
) -> dict:
    """Update an existing issue."""
    try:
        update = IssueUpdate(
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
        )
        client = get_client(interactive=False)
        issue = client.update_issue(issue_id, update)
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": str(issue.status),
            "assignee": issue.assignee,
            "due_date": issue.due_date,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating issue: {str(e)}")


@app.delete("/issues/{issue_id}")
def delete_issue(issue_id: str, token: str = Depends(oauth2_scheme)) -> dict:
    """Delete an issue."""
    try:
        client = get_client(interactive=False)
        client.delete_issue(issue_id)
        return {"status": "deleted", "issue_id": issue_id}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error deleting issue: {str(e)}")



def main():
    print("Hello from team-diamonds!")
    client = get_client(interactive=True)
    
    print("\nFetching recent issues...")
    # Let's test the get_issues generator
    try:
        issues = client.get_issues(max_results=5)
        for issue in issues:
            print(f"- {issue}")
    except Exception as e:
        print(f"Error connecting to Jira: {e}")

    try:
        issue = client.get_issue("OPS-20")
        print(f"- {issue}")
    except Exception as e:
        print(f"Error connecting to Jira: {e}")

if __name__ == "__main__":
    main()