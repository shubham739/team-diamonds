"""Jira OAuth2 authentication module for handling user login and token management."""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

JIRA_OAUTH_CLIENT_ID = os.getenv("JIRA_OAUTH_CLIENT_ID")
JIRA_OAUTH_CLIENT_SECRET = os.getenv("JIRA_OAUTH_CLIENT_SECRET")
JIRA_OAUTH_REDIRECT_URI = os.getenv("JIRA_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Jira OAuth Endpoints
JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
JIRA_API_URL = "https://api.atlassian.com/me"

# HTTP status code constant
HTTP_OK = 200

# Storing in memory for now (suitable for development, needs database for production)
user_sessions: dict[str, dict[str, Any]] = {}


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


def exchange_code_for_token(code: str) -> dict[str, Any] | None:
    """Exchange OAuth2 authorization code for access token."""
    data: dict[str, Any] = {
        "grant_type": "authorization_code",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
    }
    try:
        response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
        if response.status_code != HTTP_OK:
            logger.error("Token exchange failed: %s - %s", response.status_code, response.text)
            return None
    except requests.RequestException:
        logger.exception("Error exchanging code for token")
        return None
    else:
        result: dict[str, Any] = response.json()
        return result


def refresh_access_token(refresh_token: str) -> dict[str, Any] | None:
    """Refresh OAuth2 access token using refresh token."""
    data: dict[str, Any] = {
        "grant_type": "refresh_token",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
    if response.status_code != HTTP_OK:
        return None
    result: dict[str, Any] = response.json()
    return result


def get_user_info(access_token: str) -> dict[str, Any] | None:
    """Retrieve authenticated user information from Jira API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(JIRA_API_URL, headers=headers, timeout=10)
        if response.status_code != HTTP_OK:
            logger.error("Get user info failed: %s - %s", response.status_code, response.text)
            return None
    except requests.RequestException:
        logger.exception("Error getting user info")
        return None
    else:
        result: dict[str, Any] = response.json()
        return result


def store_session(user_id: str, token_data: dict[str, Any]) -> None:
    """Store user session with access and refresh tokens."""
    user_sessions[user_id] = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": datetime.now(UTC) + timedelta(seconds=token_data.get("expires_in", 3600)),
    }


def get_session(user_id: str) -> dict[str, Any] | None:
    """Retrieve user session data."""
    return user_sessions.get(user_id)


def is_token_expired(user_id: str) -> bool:
    """Check if user's access token has expired."""
    session = get_session(user_id)
    if not session:
        return True
    expires_at: datetime = session["expires_at"]
    return bool(datetime.now(UTC) >= expires_at)


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

    result: str = user_sessions[user_id]["access_token"]
    return result
