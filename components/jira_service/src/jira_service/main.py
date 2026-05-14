"""FastAPI server with Jira OAuth2 authentication and work management endpoints."""

import json
import hashlib
import logging
import os
from urllib.parse import parse_qs, urlparse
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import boto3
from boto3.dynamodb.conditions import Attr

import httpx
from api.issue import Status
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel

from jira_client_impl import get_client, get_oauth_client
from jira_client_impl.jira_impl import IssueNotFoundError as BaseIssueNotFoundError
from jira_service.ai_client_api import (
    GENERAL_CHAT_SYSTEM_PROMPT,
    JIRA_TOOLS,
    OpenRouterClient,
    OpenRouterError,
    get_openrouter_client,
    jira_mode_requested,
    normalize_chat_message,
)
from jira_service.auth import (
    AuthenticationError,
    create_chat_session,
    exchange_code_for_token,
    get_accessible_resources,
    get_authorize_url,
    get_session_by_token,
    get_user_info,
    store_session,
    update_session_channel,
    user_sessions,
)
from jira_service.exceptions import ClientInitializationError

IssueTrackerClient = Any

# Loading .env from inside .venv for local development
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("in main.py")

# Import Team 9's chat client API for cross-vertical integration
try:
    from chat_client_api.client import get_client as get_chat_client
    from chat_client_api.client import register_client as register_chat_client

    CHAT_CLIENT_AVAILABLE = True
except ImportError:
    get_chat_client = None  # type: ignore[assignment]
    register_chat_client = None  # type: ignore[assignment]
    CHAT_CLIENT_AVAILABLE = False
    logger.warning("Team 9's chat-client-api not available - cross-vertical integration limited")


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup: Register Slack client with Team 9's dependency injection system
    if CHAT_CLIENT_AVAILABLE and register_chat_client is not None:
        try:
            from chat_to_issues_integration.slack_client import SlackChatClient

            def create_slack_client() -> SlackChatClient:
                """Factory function for creating Slack client instances."""
                return SlackChatClient()

            register_chat_client(create_slack_client)
            logger.info("Successfully registered Slack client with Team 9's chat-client-api")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to register Slack client with Team 9: %s", e)
    
    yield
    
    # Shutdown: cleanup if needed
    pass


# FastAPI instance
app = FastAPI(
    title="Jira Service API",
    description="OAuth2-authenticated Jira work management API",
    lifespan=lifespan,
    # Use the default Swagger OAuth2 redirect path so it does not conflict
    # with our custom /auth/callback endpoint.
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": os.getenv("JIRA_OAUTH_CLIENT_ID"),
        "scopes": "read:me read:jira-work write:jira-work offline_access",
        "usePkceWithAuthorizationCodeGrant": False,
    },
    root_path="/prod",
)

# Configure CORS to allow frontend requests from CloudFront and local development
frontend_url = os.getenv("FRONTEND_URL", "https://d4m8l7smfuvyo.cloudfront.net")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://auth.atlassian.com/authorize",
    tokenUrl="https://auth.atlassian.com/oauth/token",
)

# CSRF state store (in-memory; lives for the duration of one auth round-trip)
auth_states: dict[str, str] = {}

# Cognito sub is embedded directly in the OAuth state string as "{token}|{sub}"
# so it survives the Atlassian redirect without a separate in-memory dict.


def _save_auth_state_to_dynamodb(state: str, return_url: str) -> None:
    """Persist a Team 9 OAuth return-state → URL mapping so any Lambda instance can handle the redirect."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
        table = dynamodb.Table("team-diamonds-tokens")
        table.put_item(Item={"userId": f"oauth_state:{state}", "integrationType": "oauth_state", "return_url": return_url})
        logger.info("DynamoDB: saved oauth_state for return to %s", return_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DynamoDB oauth_state save failed: %s", exc)


def _load_auth_state_from_dynamodb(state: str) -> str | None:
    """Return the return_url for a Team 9 OAuth state stored in DynamoDB, or None if not found."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
        table = dynamodb.Table("team-diamonds-tokens")
        result = table.scan(FilterExpression=Attr("userId").eq(f"oauth_state:{state}") & Attr("integrationType").eq("oauth_state"))
        items = result.get("Items", [])
        if not items:
            return None
        return_url: str = items[0].get("return_url", "")
        logger.info("DynamoDB: found oauth_state, returning to %s", return_url)
        return return_url
    except Exception as exc:  # noqa: BLE001
        logger.warning("DynamoDB oauth_state lookup failed: %s", exc)
        return None


def _write_session_to_dynamodb(item: dict[str, str]) -> None:
    """Write a session record to the team-diamonds-tokens DynamoDB table.

    Args:
        item: Dictionary with userId, integrationType, and all session fields.

    """
    if not item.get("userId"):
        logger.warning("Skipping DynamoDB write — userId is empty (cognito_sub was not provided)")
        return

    table_name = "team-diamonds-tokens"
    region = "us-east-2"
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        table.put_item(Item=item)
        logger.info("DynamoDB write succeeded for userId=%s integrationType=%s", item.get("userId"), item.get("integrationType"))
    except Exception as exc:  # noqa: BLE001
        logger.error("DynamoDB write failed: %s", exc)


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


class ChatRequest(BaseModel):
    """Request body for the AI chat endpoint."""

    message: str


class ChatRelayRequest(BaseModel):
    """Request body for the chat-relay endpoint."""

    message: str


class SelectChannelRequest(BaseModel):
    """Request body for selecting a Team 9 chat channel."""

    channel_id: str


class LoginRequest(BaseModel):
    """Request body for auth URL bootstrap requests."""

    action: str
    provider: str
    cognito_sub: str = ""


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
    # --- Try OAuth2 bearer path (works for any user from any organisation) ---
    try:
        return get_oauth_client(token)
    except OSError:
        pass  # token present but cloud lookup failed; fall through to Basic Auth

    # --- Fall back to API token / Basic Auth path (single-user / dev path) ---
    try:
        return get_client(interactive=False)
    except OSError as e:
        raise HTTPException(
            status_code=503,
            detail="Jira client not configured: set JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN",
        ) from e


def get_optional_jira_client(token: Annotated[str, Depends(oauth2_scheme)]) -> IssueTrackerClient | None:
    """Return a Jira client when available for authenticated chat requests."""
    try:
        return get_jira_client(token)
    except HTTPException:
        return None

#new
def _bootstrap_session_for_token(token: str) -> tuple[str, dict[str, Any]] | None:
    """Create a minimal in-memory session for a bearer token when missing.

    This mitigates stateless deployment behavior where callback and chat-relay
    can hit different instances and therefore lose in-memory session state.
    """
    chat_base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
    if not chat_base_url:
        return None

    chat_session_id = ""
    team9_login_url = ""
    channel_id = ""
    try:
        chat_session_id, team9_login_url = create_chat_session(chat_base_url)
    except AuthenticationError:
        logger.warning("Could not create Team 9 chat session while bootstrapping token session")
        return None

    synthetic_user_id = f"token-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}"
    store_session(
        synthetic_user_id,
        {"access_token": token},
        chat_session_id=chat_session_id,
        channel_id=channel_id,
    )
    user_sessions[synthetic_user_id]["team9_login_url"] = team9_login_url
    return get_session_by_token(token)


def _load_session_from_dynamodb(token: str) -> tuple[str, dict[str, Any]] | None:
    """Look up a persisted session in DynamoDB by Jira access token."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
        table = dynamodb.Table("team-diamonds-tokens")
        result = table.scan(
            FilterExpression=Attr("access_token").eq(token) & Attr("integrationType").eq("jira")
        )
        items = result.get("Items", [])
        if not items:
            logger.info("DynamoDB: no session found for token")
            return None
        item = items[0]
        user_id = item.get("userId", "")
        chat_session_id = item.get("chat_session_id", "")
        channel_id = item.get("channel_id", "")
        team9_login_url = item.get("team9_login_url", "")
        logger.info("DynamoDB: restored session for userId=%s chat_session_id=%s", user_id, chat_session_id)
        store_session(user_id, {"access_token": token}, chat_session_id=chat_session_id, channel_id=channel_id)
        user_sessions[user_id]["team9_login_url"] = team9_login_url
        return get_session_by_token(token)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DynamoDB session lookup failed: %s", exc)
        return None


def _get_or_bootstrap_session(token: str) -> tuple[str, dict[str, Any]] | None:
    """Return existing session for token, or lazily bootstrap one if absent."""
    existing_session = get_session_by_token(token)
    if existing_session:
        return existing_session
    session_from_db = _load_session_from_dynamodb(token)
    if session_from_db:
        return session_from_db
    return _bootstrap_session_for_token(token)

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
def login(cognito_sub: Annotated[str, Query()] = "") -> RedirectResponse:
    """Initiate OAuth2 Authorization Code flow by redirecting to Atlassian."""
    logger.info("In main.py.login /auth/login")
    state = secrets.token_urlsafe(32)
    if cognito_sub:
        state = f"{state}|{cognito_sub}"
    auth_states[state] = "jira"
    auth_url = get_authorize_url(state)
    return RedirectResponse(url=auth_url)


@app.post("/auth/login")
def login_post(payload: LoginRequest, request: Request) -> dict[str, str]:
    """Return authorization URL for frontend-initiated auth flows.

    For Jira: returns the Atlassian OAuth2 URL.
    For Slack: returns a URL to /auth/callback that initiates a Team 9 chat session only.
    """
    logger.info("In main.py.login_post /auth/login")
    if payload.action != "get_auth_url":
        raise HTTPException(status_code=400, detail="Unsupported action") from None

    provider = payload.provider.lower()
    logger.info(f"provider = {provider}")
    if provider not in ("jira", "slack"):
        raise HTTPException(status_code=400, detail="Unsupported provider") from None

    state = secrets.token_urlsafe(32)
    if payload.cognito_sub:
        state = f"{state}|{payload.cognito_sub}"
    auth_states[state] = provider

    if provider == "slack":
        callback_url = str(request.url_for("callback")) + f"?state={state}"
        return {"authUrl": callback_url}

    auth_url = get_authorize_url(state)
    return {"authUrl": auth_url}


@app.get("/auth/callback", response_model=None)
def callback(
    csrf_state: Annotated[str, Query(alias="state")],
    authorization_code: Annotated[str | None, Query(alias="code")] = None,
) -> RedirectResponse | dict[str, str | None]:
    """OAuth2 callback endpoint — handles both Jira and Slack connect flows.

    For Jira: validates state, exchanges the authorization code for tokens,
    fetches the user's Atlassian account info, creates a Team 9 chat session,
    and stores the session before redirecting to /jira/callback.

    For Slack: creates a Team 9 chat session only (no OAuth) and redirects home.

    Args:
        csrf_state: CSRF state token (must match one issued by /auth/login).
        authorization_code: OAuth authorization code from Atlassian (Jira only).

    Returns:
        Redirect to the frontend /jira/callback (Jira) or home page (Slack).

    Raises:
        HTTPException 400: If state is invalid or token exchange fails.
    """
    logger.info("In main.py.callback /auth/callback")
    # Extract embedded cognito_sub from state (format: "{token}|{sub}" or just "{token}")
    embedded_cognito_sub = csrf_state.rsplit("|", 1)[1] if "|" in csrf_state else ""

    provider = auth_states.get(csrf_state)
    frontend_url = os.getenv("FRONTEND_URL", "https://d4m8l7smfuvyo.cloudfront.net")

    # State not in this Lambda instance's memory — check DynamoDB (handles cross-instance redirects)
    if provider is None:
        return_url = _load_auth_state_from_dynamodb(csrf_state)
        if return_url:
            return RedirectResponse(url=return_url)
        logger.warning("CALLBACK: unknown state=%s", csrf_state)
        raise HTTPException(status_code=400, detail="Invalid state") from None

    if provider not in ("jira", "slack") and not provider.startswith("return:"):
        logger.warning("CALLBACK: unknown state=%s", csrf_state)
        raise HTTPException(status_code=400, detail="Invalid state") from None

    # ── Team 9 return: auth completed, send user to stored destination ────────
    if provider.startswith("return:"):
        return_url = provider[len("return:"):]
        del auth_states[csrf_state]
        logger.info("TEAM9 RETURN: redirecting to %s", return_url)
        return RedirectResponse(url=return_url)

    # ── Slack: chat session only, no OAuth ────────────────────────────────────
    if provider == "slack":
        user_id: str = ""
        chat_session_id: str = ""
        team9_login_url: str | None = None
        channel_id: str = ""
        # chat_base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
        chat_base_url = "https://os-bmaq.onrender.com"
        if chat_base_url:
            try:
                chat_session_id, team9_login_url = create_chat_session(chat_base_url)
            except AuthenticationError:
                logger.warning("Could not create Team 9 chat session for user %s", user_id)

            if chat_session_id:
                try:
                    with httpx.Client(timeout=10) as http:
                        ch_resp = http.get(f"{chat_base_url}/channels", headers={"X-Session-ID": chat_session_id})
                        ch_resp.raise_for_status()
                        channels = ch_resp.json().get("channels", [])
                        if channels:
                            channel_id = channels[0].get("channel_id", "")
                            logger.info("Auto-selected channel %s for user %s", channel_id, user_id)
                except Exception:  # noqa: BLE001
                    logger.warning("Could not auto-select Team 9 channel for user %s", user_id)

        store_session(user_id, {}, chat_session_id=chat_session_id, channel_id=channel_id)

        slack_cognito_sub = embedded_cognito_sub
        slack_dynamo_item: dict[str, str] = {
            "userId": slack_cognito_sub,
            "integrationType": "slack",
            "chat_session_id": chat_session_id,
            "channel_id": channel_id,
        }
        logger.info("Sending to DynamoDB (slack): %s", slack_dynamo_item)
        _write_session_to_dynamodb(slack_dynamo_item)

        del auth_states[csrf_state]
        if team9_login_url:
            team9_state = parse_qs(urlparse(team9_login_url).query).get("state", [""])[0]
            if team9_state:
                auth_states[team9_state] = f"return:{frontend_url}"
                _save_auth_state_to_dynamodb(team9_state, frontend_url)
            return RedirectResponse(url=team9_login_url)
        return RedirectResponse(url=frontend_url)

    # ── Jira: full OAuth flow ─────────────────────────────────────────────────
    logger.info("In authcallback jira oAuth flow.")
    if not authorization_code:
        raise HTTPException(status_code=400, detail="Missing authorization code") from None

    try:
        token_data = exchange_code_for_token(authorization_code)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token") from e

    access_token: str = token_data.get("access_token", "")

    try:
        user_info = get_user_info(access_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail="Failed to get user info") from e

    jira_user_id: str = user_info.get("account_id", "")
    cloud_id: str = ""

    try:
        resources = get_accessible_resources(access_token)
        cloud_id = resources[0]["id"] if resources else ""
    except Exception:  # noqa: BLE001
        logger.warning("Could not fetch accessible resources for user %s", jira_user_id)

    chat_session_id_jira: str = ""
    team9_login_url_jira: str = ""
    channel_id_jira: str = ""
    chat_base_url_jira = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
    if chat_base_url_jira:
        try:
            chat_session_id_jira, team9_login_url_jira = create_chat_session(chat_base_url_jira)
        except AuthenticationError:
            logger.warning("Could not create Team 9 chat session for user %s", jira_user_id)

    store_session(jira_user_id, token_data, cloud_id, chat_session_id=chat_session_id_jira, channel_id=channel_id_jira)

    jira_cognito_sub = embedded_cognito_sub
    user_sessions[jira_user_id]["team9_login_url"] = team9_login_url_jira

    jira_dynamo_item: dict[str, str] = {
        "userId": jira_cognito_sub,
        "integrationType": "jira",
        "access_token": token_data.get("access_token", "") or "",
        "chat_session_id": chat_session_id_jira,
        "channel_id": channel_id_jira,
        "team9_login_url": team9_login_url_jira,
    }
    logger.info("Sending to DynamoDB (jira): %s", jira_dynamo_item)
    _write_session_to_dynamodb(jira_dynamo_item)

    del auth_states[csrf_state]
    jira_callback_url = f"{frontend_url}/jira/callback?access_token={access_token}&user_id={jira_user_id}"
    return RedirectResponse(url=jira_callback_url)

@app.get("/auth/channels")
def list_chat_channels(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, Any]:
    """Return the Team 9 chat channels available to the authenticated user.

    Requires the user to have completed the full OAuth2 callback (so that a
    Team 9 session ID is stored alongside their Jira token).

    Raises:
        HTTPException 401: No Jira session found for this token.
        HTTPException 400: Jira session exists but has no Team 9 session linked.
        HTTPException 503: CHAT_CLIENT_SERVICE_BASE_URL not configured.
        HTTPException 502: Team 9 service returned an error.

    """
    #new
    session_info = _get_or_bootstrap_session(token)
    if not session_info:
        raise HTTPException(status_code=401, detail="No session found. Complete the OAuth2 flow at /auth/login first.")
    _, session = session_info
    chat_session_id: str = session.get("chat_session_id", "")
    if not chat_session_id:
        raise HTTPException(status_code=400, detail="No Team 9 session linked. Visit /auth/callback first.")
    base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=503, detail="CHAT_CLIENT_SERVICE_BASE_URL not configured.")
    try:
        with httpx.Client(timeout=10) as http:
            response = http.get(f"{base_url}/channels", headers={"X-Session-ID": chat_session_id})
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch channels from chat service.") from exc
    return response.json()  # type: ignore[no-any-return]


@app.post("/auth/select-channel")
def select_channel(
    body: SelectChannelRequest,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, str]:
    """Store the user's chosen Team 9 chat channel for use in /chat-relay.

    Must be called after the user has picked a channel from GET /auth/channels.

    Raises:
        HTTPException 401: No session found for this token.

    """
    #new
    session_info = _get_or_bootstrap_session(token)
    if not session_info:
        raise HTTPException(status_code=401, detail="No session found. Complete the OAuth2 flow at /auth/login first.")
    user_id, _ = session_info
    update_session_channel(user_id, body.channel_id)
    return {"status": "ok", "channel_id": body.channel_id}


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
        max_results: Maximum number of results to return (1-100).

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


# ---------------------------------------------------------------------------
# Chat Endpoint (AI value-add — all /issues endpoints remain fully accessible)
# ---------------------------------------------------------------------------

def _parse_status_arg(status_val: Any) -> Status | None:  # noqa: ANN401
    """Normalize tool-call status values into the canonical ``Status`` enum."""
    if status_val is None:
        return None
    normalized = str(status_val).strip().lower().replace("status.", "")
    normalized = normalized.replace("-", "_").replace(" ", "_")
    status_aliases = {
        "todo": "to_do",
        "to_do": "to_do",
        "inprogress": "in_progress",
        "in_progress": "in_progress",
        "complete": "completed",
        "completed": "completed",
        "done": "completed",
        "cancelled": "completed",
        "canceled": "completed",
    }
    canonical = status_aliases.get(normalized, normalized)
    return Status(canonical)

def _execute_tool(name: str, args: dict[str, Any], client: IssueTrackerClient) -> Any:  # noqa: ANN401
    """Dispatch a single LLM tool call to the Jira client and return a JSON-serialisable result."""
    if name == "list_issues":
        status_val: str | None = args.get("status")
        issues = list(
            client.get_issues(
                title=args.get("title"),
                desc=args.get("desc"),
                status=_parse_status_arg(status_val),
                members=args.get("members"),
                due_date=args.get("due_date"),
                max_results=int(args.get("max_results", 20)),
            ),
        )
        return [_issue_to_dict(i) for i in issues]

    if name == "get_issue":
        return _issue_to_dict(client.get_issue(args["issue_id"]))

    if name == "create_issue":
        status_val = args.get("status")
        issue = client.create_issue(
            title=args.get("title"),
            desc=args.get("desc"),
            status=_parse_status_arg(status_val),
            members=args.get("members"),
            due_date=args.get("due_date"),
            board_id=args.get("board_id"),
        )
        return _issue_to_dict(issue)

    if name == "update_issue":
        issue_id = args["issue_id"]
        status_val = args.get("status")
        target_status = _parse_status_arg(status_val)

        # Jira transitions can error when asking for the same status; treat this as a successful no-op.
        if target_status is not None:
            current_issue = client.get_issue(issue_id)
            current_status_raw = getattr(current_issue, "status", None)
            current_status = _parse_status_arg(current_status_raw)
            if current_status == target_status:
                return _issue_to_dict(current_issue)

        try:
            return _issue_to_dict(client.update_issue(
                issue_id,
                title=args.get("title"),
                desc=args.get("desc"),
                status=target_status,
                members=args.get("members"),
                due_date=args.get("due_date"),
                board_id=args.get("board_id"),
            ))
        except Exception as update_error:  # noqa: BLE001
            # Some Jira workflows apply the transition but still return an error on follow-up read.
            if target_status is not None:
                try:
                    post_update_issue = client.get_issue(issue_id)
                    post_update_status = _parse_status_arg(getattr(post_update_issue, "status", None))
                    if post_update_status == target_status:
                        return _issue_to_dict(post_update_issue)
                except Exception:  # noqa: BLE001
                    pass
            raise update_error

    if name == "delete_issue":
        client.delete_issue(args["issue_id"])
        return {"status": "deleted", "issue_id": args["issue_id"]}

    msg = f"Unknown tool: {name!r}"
    raise ValueError(msg)


def _run_chat_loop(
    user_message: str,
    jira_client: IssueTrackerClient | None,
    openrouter: OpenRouterClient,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the agentic tool-use loop and return (reply_text, actions_taken)."""
    jira_enabled = jira_mode_requested(user_message)
    if jira_enabled and jira_client is None:
        return "Jira is not connected right now. Connect Jira first, then try your @jira request again.", []
    normalized_message = normalize_chat_message(user_message)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": GENERAL_CHAT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Jira mode is enabled for this request. The user explicitly asked for Jira help, "
                "so you may use Jira tools if they are helpful."
                if jira_enabled
                else "Jira mode is not enabled for this request. Do not use Jira tools."
            ),
        },
        {"role": "user", "content": normalized_message},
    ]
    actions: list[dict[str, Any]] = []

    for _ in range(3):
        response = openrouter.complete(messages, tools=JIRA_TOOLS if jira_enabled else None)
        choices = response.get("choices") if isinstance(response, dict) else None
        if not isinstance(choices, list) or not choices:
            return "I could not process the model response. Please try again.", actions

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return "I could not process the model response. Please try again.", actions

        choice = first_choice
        assistant_message = choice.get("message")
        if not isinstance(assistant_message, dict):
            return "I could not process the model response. Please try again.", actions

        messages.append(assistant_message)

        tool_calls = assistant_message.get("tool_calls")
        if choice.get("finish_reason") != "tool_calls" or not isinstance(tool_calls, list) or not tool_calls:
            return assistant_message.get("content") or "Done.", actions

        for tool_call in tool_calls:
            function_block = tool_call.get("function") if isinstance(tool_call, dict) else None
            tool_name = function_block.get("name") if isinstance(function_block, dict) else None
            raw_arguments = function_block.get("arguments") if isinstance(function_block, dict) else None

            if not tool_name:
                continue

            if isinstance(raw_arguments, dict):
                tool_args = raw_arguments
            elif isinstance(raw_arguments, str):
                try:
                    parsed_arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    parsed_arguments = {"_parse_error": "Invalid JSON arguments from model"}
                tool_args = parsed_arguments if isinstance(parsed_arguments, dict) else {}
            else:
                tool_args = {}

            try:
                result = _execute_tool(tool_name, tool_args, jira_client)
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc)}
            actions.append({"tool": tool_name, "args": tool_args, "result": result})
            tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else None
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id or f"tool_call_{len(actions)}",
                "content": json.dumps(result),
            })

    return "I was unable to complete the request within the allowed steps.", actions


@app.post("/chat")
def chat(
    body: ChatRequest,
    client: Annotated[IssueTrackerClient | None, Depends(get_optional_jira_client)],
    openrouter: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
) -> dict[str, Any]:
    """Natural-language Jira assistant powered by OpenRouter.

    The LLM interprets the user's message and calls Jira tools as needed.
    All existing /issues endpoints remain fully accessible alongside this endpoint.

    Args:
        body: Chat request containing a ``message`` field.
        client: Jira client (injected).
        openrouter: OpenRouter LLM client (injected).

    Returns:
        ``{"reply": str, "actions": list}`` — the assistant's response and
        the list of Jira tool calls that were executed.

    Raises:
        HTTPException 502: If OpenRouter returns an error.
        HTTPException 500: On unexpected errors.

    """
    try:
        reply, actions = _run_chat_loop(body.message, client, openrouter)
    except OpenRouterError as e:
        logger.exception("OpenRouter error")
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error in /chat")
        raise HTTPException(status_code=500, detail="Unexpected error in chat") from e
    else:
        return {"reply": reply, "actions": actions}


def _notify_chat_service(channel_id: str, text: str, session_id: str) -> bool:
    """Post a message to Team 9's chat service.

    Returns True if the message was delivered successfully, False otherwise.
    Logs the full response body on failure so errors are visible in CloudWatch.
    """
    if CHAT_CLIENT_AVAILABLE and get_chat_client is not None:
        try:
            chat_client = get_chat_client()
            chat_client.send_message(channel_id, text)
            logger.info("Successfully sent message to channel %s via Team 9's chat client", channel_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to use Team 9's chat client, falling back to HTTP: %s", exc)

    base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
    if not base_url:
        logger.warning("CHAT_CLIENT_SERVICE_BASE_URL not set — skipping notification")
        return False
    try:
        with httpx.Client(timeout=10) as http:
            resp = http.post(
                f"{base_url}/messages",
                json={"channel": channel_id, "text": text},
                headers={"X-Session-ID": session_id},
            )
        if resp.is_success:
            logger.info("POST /messages succeeded for channel=%s session=%s", channel_id, session_id)
            return True
        logger.warning(
            "POST /messages failed: status=%s channel=%s session=%s body=%s",
            resp.status_code,
            channel_id,
            session_id,
            resp.text[:500],
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("POST /messages error for channel=%s session=%s: %s", channel_id, session_id, exc)
        return False


def _persist_channel_to_dynamodb(token: str, channel_id: str) -> None:
    """Write the selected channel_id back to the DynamoDB session record found by access_token."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
        table = dynamodb.Table("team-diamonds-tokens")
        result = table.scan(
            FilterExpression=Attr("access_token").eq(token) & Attr("integrationType").eq("jira")
        )
        items = result.get("Items", [])
        if items:
            table.put_item(Item={**items[0], "channel_id": channel_id})
            logger.info("DynamoDB: persisted channel_id=%s for userId=%s", channel_id, items[0].get("userId"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("DynamoDB channel_id persist failed: %s", exc)


@app.post("/chat-relay")
def chat_relay(
    body: ChatRelayRequest,
    token: Annotated[str, Depends(oauth2_scheme)],
    client: Annotated[IssueTrackerClient, Depends(get_jira_client)],
    openrouter: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
) -> dict[str, Any]:
    """Natural-language Jira assistant that replies via the Team 9 chat service.

    Runs the same AI chat logic as POST /chat, then posts the reply to the
    channel the user selected via POST /auth/select-channel.

    The full onboarding flow before calling this endpoint:
        1. GET  /auth/login            — Jira OAuth2
        2. GET  /auth/channels         — list Team 9 channels
        3. POST /auth/select-channel   — pick a channel

    Returns:
        ``{"reply": str, "actions": list}`` — same shape as /chat.

    Raises:
        HTTPException 401: No session found for this token.
        HTTPException 400: Channel or Team 9 session not yet configured.
        HTTPException 502: If OpenRouter returns an error.
        HTTPException 500: On unexpected errors.

    """
    session_info = _get_or_bootstrap_session(token)
    if not session_info:
        raise HTTPException(status_code=401, detail="No session found. Complete the OAuth2 flow at /auth/login first.")
    user_id, session = session_info
    chat_session_id: str = session.get("chat_session_id", "")

    if not chat_session_id:
        raise HTTPException(status_code=400, detail="No Team 9 session linked. Complete /auth/callback first.")

    team9_login_url: str = session.get("team9_login_url", "")
    configured_channel = os.environ.get("TEAM9_CHANNEL_ID", "").strip()
    channel_id: str = configured_channel or session.get("channel_id", "")
    if configured_channel:
        logger.info("Using configured TEAM9_CHANNEL_ID=%s", channel_id)
    all_channels: list[dict[str, str]] = []
    if not channel_id:
        base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
        logger.info("Auto-select: using chat_session_id=%s for user=%s", chat_session_id, user_id)
        try:
            with httpx.Client(timeout=10) as http:
                ch_resp = http.get(f"{base_url}/channels", headers={"X-Session-ID": chat_session_id})
                ch_resp.raise_for_status()
                all_channels = ch_resp.json().get("channels", [])
                logger.info(
                    "Available Team 9 channels: %s",
                    [(c.get("channel_id"), c.get("name")) for c in all_channels],
                )
                if all_channels:
                    channel_id = all_channels[0].get("channel_id", "")
                    if channel_id:
                        update_session_channel(user_id, channel_id)
                        _persist_channel_to_dynamodb(token, channel_id)
                        logger.info(
                            "Auto-selected channel %s (%s) for user %s",
                            channel_id,
                            all_channels[0].get("name"),
                            user_id,
                        )
        except httpx.HTTPStatusError as exc:
            logger.warning("Auto-select Team 9 channel failed for user %s: %s", user_id, exc)
            if exc.response.status_code == 401 and team9_login_url:
                return {
                    "reply": (
                        "Your Team 9 Slack session needs to be authenticated before I can relay messages.\n\n"
                        f"[**Authenticate with Team 9 here**]({team9_login_url})\n\n"
                        "After completing the Slack login, send your message again."
                    ),
                    "actions": [],
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Auto-select Team 9 channel failed for user %s: %s", user_id, exc)
        if not channel_id:
            raise HTTPException(status_code=400, detail="No channel available. Ensure the bot is in a Slack channel.")

    try:
        reply, actions = _run_chat_loop(body.message, client, openrouter)
    except OpenRouterError as e:
        logger.exception("OpenRouter error in /chat-relay")
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error in /chat-relay")
        raise HTTPException(status_code=500, detail="Unexpected error in chat-relay") from e

    # Try the stored channel first; if it fails, iterate through remaining channels.
    posted = _notify_chat_service(channel_id, reply, chat_session_id)
    if not posted:
        remaining = [c for c in all_channels if c.get("channel_id") and c.get("channel_id") != channel_id]
        for candidate in remaining:
            cid = candidate.get("channel_id", "")
            logger.info("Retrying POST /messages with channel %s (%s)", cid, candidate.get("name"))
            posted = _notify_chat_service(cid, reply, chat_session_id)
            if posted:
                update_session_channel(user_id, cid)
                _persist_channel_to_dynamodb(token, cid)
                channel_id = cid
                break

    if not posted and team9_login_url:
        reply = (
            reply
            + "\n\n---\n⚠️ Could not post to Slack — your Team 9 session needs authentication.\n\n"
            f"[**Authenticate with Team 9 here**]({team9_login_url})\n\n"
            "After completing the Slack login, send your message again."
        )
    return {"reply": reply, "actions": actions}