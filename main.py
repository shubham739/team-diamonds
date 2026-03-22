#This file is for development purposes only

import os
from dotenv import load_dotenv

# loading .env from inside .venv
venv_env_path = os.path.join(os.path.dirname(__file__), '.venv', '.env')
load_dotenv(venv_env_path)

import logging
import secrets
from jira_client_impl import get_client
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from auth import (
    get_authorize_url,
    exchange_code_for_token,
    get_user_info,
    store_session,
    get_valid_token,
    user_sessions,
)


#fast API connection to the server
app = FastAPI()

auth_states: dict[str, str] = {}


@app.get("/health")
def health_check():
    client = get_client(interactive=True)
    return {"status": "ok"}


@app.get("/auth/login")
def login():
    state = secrets.token_urlsafe(32)
    auth_states[state] = state
    auth_url = get_authorize_url(state)
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def callback(code: str, state: str):
    if state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    token_data = exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    
    access_token = token_data.get("access_token")
    user_info = get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    user_id = user_info.get("account_id")
    store_session(user_id, token_data)
    del auth_states[state]
    
    return {
        "status": "authenticated",
        "user_id": user_id,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
    }


@app.get("/auth/logout")
def logout(user_id: str):
    if user_id in user_sessions:
        del user_sessions[user_id]
    return {"status": "logged out"}

@app.get("/")
def root():
    client = get_client(interactive=True)
    return {"message": client.get_issues(max_results=5)}



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