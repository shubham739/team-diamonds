"""Jira OAuth2 authentication module for handling user login and token management."""

import os
from datetime import UTC, datetime, timedelta

import requests
from fastapi import HTTPException

JIRA_OAUTH_CLIENT_ID = os.getenv("JIRA_OAUTH_CLIENT_ID")
JIRA_OAUTH_CLIENT_SECRET = os.getenv("JIRA_OAUTH_CLIENT_SECRET")
JIRA_OAUTH_REDIRECT_URI = os.getenv("JIRA_OAUTH_REDIRECT_URI","http://localhost:8000/auth/callback")


# Jira OAuth Endpoints
JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"  # noqa: S105
JIRA_API_URL = "https://api.atlassian.com/me"

# HTTP status code constant
HTTP_OK = 200

# Storing in memory for now (suitable for development, needs database for production)
user_sessions: dict[str, dict] = {}

def get_authorize_url(state: str) -> str:
    """Generate Jira OAuth authorization URL."""
    params = {
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "scope": "read:me read:jira-work write:jira-work offline_access",
        "prompt": "consent",
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{JIRA_AUTH_URL}?{query_string}"

def exchange_code_for_token(code: str) -> dict | None:
    """Exchange OAuth2 authorization code for access token."""
    data = {
        "grant_type": "authorization_code",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
    }
    try:
        response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
        if response.status_code != HTTP_OK:
            print(f"Token exchange failed: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error exchanging code for token: {e}")
        return None


def refresh_access_token(refresh_token: str) -> dict | None:
    """Refresh OAuth2 access token using refresh token."""
    data = {
        "grant_type": "refresh_token",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
    if response.status_code != HTTP_OK:
        return None
    return response.json()

def get_user_info(access_token: str) -> dict | None:
    """Retrieve authenticated user information from Jira API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(JIRA_API_URL, headers=headers, timeout=10)
        if response.status_code != HTTP_OK:
            print(f"Get user info failed: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None

def store_session(user_id: str, token_data: dict) -> None:
    """Store user session with access and refresh tokens."""
    user_sessions[user_id] = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": datetime.now(UTC)
        + timedelta(seconds=token_data.get("expires_in", 3600)),
    }

def get_session(user_id: str) -> dict | None:
    """Retrieve user session data."""
    return user_sessions.get(user_id)


def is_token_expired(user_id: str) -> bool:
    """Check if user's access token has expired."""
    session = get_session(user_id)
    if not session:
        return True
    return datetime.now(UTC) >= session["expires_at"]


def get_valid_token(user_id: str) -> str | None:
    """Get valid token for user, refreshing if needed."""
    session = get_session(user_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if is_token_expired(user_id):
        new_token = refresh_access_token(session["refresh_token"])
        if not new_token:
            raise HTTPException(status_code=401, detail="Token refresh failed")
        store_session(user_id, new_token)

    return user_sessions[user_id]["access_token"]
