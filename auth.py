import os
import requests
from typing import Optional
from fastapi import HTTPException, params, status
from datetime import datetime, timedelta, timezone

JIRA_OAUTH_CLIENT_ID = os.getenv("JIRA_OAUTH_CLIENT_ID")
JIRA_OAUTH_CLIENT_SECRET = os.getenv("JIRA_OAUTH_CLIENT_SECRET")
JIRA_OAUTH_REDIRECT_URI = os.getenv("JIRA_OAUTH_REDIRECT_URI","http://localhost:8000/auth/callback")


# Jira OAuth Endpoints
JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
JIRA_API_URL = "https://api.atlassian.com/me"

#storing in memory for now
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

def exchange_code_for_token(code: str) -> Optional[dict]:
    # Exchanging the authorization code for an access token
    data = {
        "grant_type": "authorization_code",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_OAUTH_REDIRECT_URI,
    }
    response = requests.post(JIRA_TOKEN_URL, data=data)
    if response.status_code != 200:
        print(f"Token exchange failed: {response.text}")
        return None
    return response.json()


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    # Refreshing the access token using the refresh token
    data = {
        "grant_type": "refresh_token",
        "client_id": JIRA_OAUTH_CLIENT_ID,
        "client_secret": JIRA_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    response = requests.post(JIRA_TOKEN_URL, data=data)
    if response.status_code != 200:
        return None
    return response.json()

def get_user_info(access_token: str) -> Optional[dict]:
    # Fetching user info from Jira using the access token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(JIRA_API_URL, headers=headers)
    
    print(f"User info response status: {response.status_code}")
    print(f"User info response body: {response.text}")
    
    if response.status_code != 200:
        print(f"Failed to get user info: {response.text}")
        return None
    
    return response.json()

def store_session(user_id: str, token_data: dict):
    # Store the access token and refresh token in memory (for demo purposes)
    user_sessions[user_id] = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
    }

def get_session(user_id: str) -> Optional[dict]:
    # Retrieve the session for a user
    return user_sessions.get(user_id)


def is_token_expired(user_id: str) -> bool:
    # Check if the access token for the user has expired
    session = get_session(user_id)
    if not session:
        return True
    return datetime.now(timezone.utc) >= session["expires_at"]


def get_valid_token(user_id: str) -> Optional[str]:
    """Get valid token, refreshing if needed."""
    session = get_session(user_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if is_token_expired(user_id):
        new_token = refresh_access_token(session["refresh_token"])
        if not new_token:
            raise HTTPException(status_code=401, detail="Token refresh failed")
        store_session(user_id, new_token)
    
    return user_sessions[user_id]["access_token"]