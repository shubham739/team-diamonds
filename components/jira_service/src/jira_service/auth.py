"""Jira OAuth2 authentication module for handling user login and token management."""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger()

JIRA_OAUTH_CLIENT_ID = os.getenv("JIRA_OAUTH_CLIENT_ID")
JIRA_OAUTH_CLIENT_SECRET = os.getenv("JIRA_OAUTH_CLIENT_SECRET")
JIRA_OAUTH_REDIRECT_URI = os.getenv("JIRA_OAUTH_REDIRECT_URI", "https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/auth/callback")

# Jira OAuth Endpoints
JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"  # noqa: S105
JIRA_API_URL = "https://api.atlassian.com/me"

# HTTP status code constant
HTTP_OK = 200

# Log OAuth configuration status at startup
logger.info(
    "OAuth Config: client_id=%s, redirect_uri=%s",
    "SET" if JIRA_OAUTH_CLIENT_ID else "NOT SET",
    JIRA_OAUTH_REDIRECT_URI,
)


class AuthenticationError(Exception):
    """Raised when OAuth or authentication operations fail."""


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""


# Storing in memory for now (suitable for development, needs database for production)
user_sessions: dict[str, dict[str, Any]] = {}


def get_authorize_url(state: str) -> str:
    """Generate Jira OAuth authorization URL.

    Args:
        state: CSRF token for security

    Returns:
        Authorization URL for OAuth flow

    """
    logger.info("in auth.py.get_authorize_url:")
    if not JIRA_OAUTH_CLIENT_ID:
        msg = "JIRA_OAUTH_CLIENT_ID is not configured. Set the environment variable before requesting auth."
        logger.error(msg)
        raise AuthenticationError(msg)

    params = {
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "scope": "read:me read:jira-work write:jira-work offline_access",
    }
    query_string = urlencode(params)
    auth_url = f"{JIRA_AUTH_URL}?{query_string}"
    logger.info("Generated Jira OAuth URL with client_id=%s, redirect_uri=%s", JIRA_OAUTH_CLIENT_ID, JIRA_OAUTH_REDIRECT_URI)
    logger.info("auth_url = %s", auth_url)
    return auth_url


def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange OAuth2 authorization code for access token.

    Args:
        code: Authorization code from OAuth provider

    Returns:
        Token data dictionary with access_token, refresh_token, etc.

    Raises:
        AuthenticationError: If token exchange fails

    """
    data: dict[str, Any] = {
        "grant_type": "authorization_code",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
    }
    try:
        response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except requests.RequestException as e:
        msg = "Failed to exchange authorization code for token"
        logger.exception(msg)
        raise AuthenticationError(msg) from e


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh OAuth2 access token using refresh token.

    Args:
        refresh_token: Refresh token from previous auth

    Returns:
        New token data dictionary

    Raises:
        TokenRefreshError: If refresh fails

    """
    data: dict[str, Any] = {
        "grant_type": "refresh_token",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    try:
        response = requests.post(JIRA_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except requests.RequestException as e:
        msg = "Failed to refresh access token"
        logger.exception(msg)
        raise TokenRefreshError(msg) from e


def get_user_info(access_token: str) -> dict[str, Any]:
    """Retrieve authenticated user information from Jira API.

    Args:
        access_token: OAuth access token

    Returns:
        User info dictionary with account_id, email, name, etc.

    Raises:
        AuthenticationError: If user info retrieval fails

    """
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(JIRA_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except requests.RequestException as e:
        msg = "Failed to retrieve user information"
        logger.exception(msg)
        raise AuthenticationError(msg) from e


def create_chat_session(base_url: str) -> tuple[str, str]:
    """Create a new Team 9 chat session.

    Args:
        base_url: Base URL of Team 9's chat service.

    Returns:
        ``(session_id, login_url)`` tuple.

    Raises:
        AuthenticationError: If the request fails or the response is malformed.

    """
    logger.info("In auth.py/create_chat_session:")
    try:
        response = requests.post(f"{base_url}/auth/sessions", timeout=60)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data["session_id"], data["login_url"]
    except (requests.RequestException, KeyError) as e:
        msg = "Failed to create Team 9 chat session"
        raise AuthenticationError(msg) from e


def get_accessible_resources(access_token: str) -> list[dict[str, Any]]:
    """Fetch the list of Atlassian cloud sites accessible to this token.

    Args:
        access_token: A valid Atlassian OAuth2 access token.

    Returns:
        List of resource dicts, each containing at minimum an "id" (cloud ID).

    Raises:
        AuthenticationError: If the request fails.

    """
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except requests.RequestException as e:
        msg = "Failed to fetch accessible Atlassian resources"
        logger.exception(msg)
        raise AuthenticationError(msg) from e


def store_session(
    user_id: str,
    token_data: dict[str, Any],
    cloud_id: str = "",
    chat_session_id: str = "",
    channel_id: str = "",
) -> None:
    """Store user session with access and refresh tokens.

    Args:
        user_id: Unique user identifier
        token_data: Token response data
        cloud_id: Atlassian cloud ID for this user's Jira instance
        chat_session_id: Team 9 chat service session ID
        channel_id: Selected Team 9 chat channel ID

    """
    user_sessions[user_id] = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": datetime.now(UTC) + timedelta(seconds=token_data.get("expires_in", 3600)),
        "cloud_id": cloud_id,
        "chat_session_id": chat_session_id,
        "channel_id": channel_id,
    }


def update_session_channel(user_id: str, channel_id: str) -> None:
    """Store the user's selected chat channel in their existing session.

    Args:
        user_id: Unique user identifier
        channel_id: Team 9 chat channel ID chosen by the user

    """
    if user_id in user_sessions:
        user_sessions[user_id]["channel_id"] = channel_id


def get_session_by_token(access_token: str) -> tuple[str, dict[str, Any]] | None:
    """Find a session by its access token.

    Args:
        access_token: Atlassian OAuth2 access token.

    Returns:
        ``(user_id, session)`` if found, otherwise ``None``.

    """
    for user_id, session in user_sessions.items():
        if session.get("access_token") == access_token:
            return user_id, session
    return None


def get_session(user_id: str) -> dict[str, Any] | None:
    """Retrieve user session data.

    Args:
        user_id: Unique user identifier

    Returns:
        Session data or None if not found

    """
    return user_sessions.get(user_id)


def is_token_expired(user_id: str) -> bool:
    """Check if user's access token has expired.

    Args:
        user_id: Unique user identifier

    Returns:
        True if token is expired, False otherwise

    """
    session = get_session(user_id)
    if not session:
        return True
    expires_at: datetime = session["expires_at"]
    return bool(datetime.now(UTC) >= expires_at)


def get_valid_token(user_id: str) -> str:
    """Get valid token for user, refreshing if needed.

    Args:
        user_id: Unique user identifier

    Returns:
        Valid access token

    Raises:
        AuthenticationError: If user not authenticated
        TokenRefreshError: If token refresh fails

    """
    session = get_session(user_id)
    if not session:
        msg = "User not authenticated"
        raise AuthenticationError(msg) from None

    if is_token_expired(user_id):
        new_token = refresh_access_token(session["refresh_token"])
        store_session(user_id, new_token)

    return user_sessions[user_id]["access_token"]  # type: ignore[no-any-return]
