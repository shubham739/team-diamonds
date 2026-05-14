"""Jira Chat Bridge.

Connects Team 9's Chat Client Service to this team's Jira AI /chat endpoint.

Registration flow (called by the website after the user completes Jira OAuth2):
    POST /sessions  {"channel_id": "C123", "token": "<atlassian_access_token>"}

Message flow (runs continuously in the background):
    Team 9 GET  /messages?channel=C123   <- poll for new user messages
    Our   POST /chat  {"message": "..."}  <- Jira AI processes the request
    Team 9 POST /messages  {"channel": "C123", "text": "<reply>"}  <- send reply

Logout flow:
    DELETE /sessions/{channel_id}

Required environment variables:
    CHAT_CLIENT_SERVICE_BASE_URL    Base URL of Team 9's chat client service
    CHAT_CLIENT_SERVICE_SESSION_ID  Authenticated session ID for Team 9's service
    JIRA_SERVICE_BASE_URL           Base URL of this team's Jira service
    POLL_INTERVAL_SECONDS           Seconds between polls per channel (default: 3)
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

load_dotenv(".venv/.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# channel_id -> {"token": str, "last_ts": str | None}
_sessions: dict[str, dict[str, Any]] = {}


class RegisterSessionRequest(BaseModel):
    """Request body for registering a user session."""

    channel_id: str
    token: str


def _chat_base_url() -> str:
    return os.getenv("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")


def _chat_session_id() -> str:
    return os.getenv("CHAT_CLIENT_SERVICE_SESSION_ID", "")


def _jira_base_url() -> str:
    return os.getenv("JIRA_SERVICE_BASE_URL", "").rstrip("/")


def _poll_interval() -> float:
    return float(os.getenv("POLL_INTERVAL_SECONDS", "3"))


async def _get_new_messages(
    channel_id: str,
    after_ts: str | None,
) -> list[dict[str, Any]]:
    """Fetch messages from Team 9's service, filtering to only those after after_ts."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{_chat_base_url()}/messages",
            params={"channel": channel_id, "limit": 20},
            headers={"X-Session-ID": _chat_session_id()},
        )
        response.raise_for_status()

    messages: list[dict[str, Any]] = response.json().get("messages", [])
    if after_ts:
        messages = [m for m in messages if m.get("timestamp", "") > after_ts]
    return messages


async def _call_jira_chat(message: str, token: str) -> str:
    """Forward a message to the Jira /chat endpoint and return the reply."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{_jira_base_url()}/chat",
            json={"message": message},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

    data: dict[str, Any] = response.json()
    return str(data.get("reply", "No reply received."))


async def _send_reply(channel_id: str, text: str) -> str:
    """Post a reply to Team 9's service and return the new message timestamp."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{_chat_base_url()}/messages",
            json={"channel": channel_id, "text": text},
            headers={"X-Session-ID": _chat_session_id()},
        )
        response.raise_for_status()

    data: dict[str, Any] = response.json()
    return str(data.get("timestamp", ""))


async def _poll_channel(channel_id: str, session: dict[str, Any]) -> None:
    """Process any new messages on a single registered channel."""
    token: str = session["token"]
    last_ts: str | None = session.get("last_ts")

    try:
        messages = await _get_new_messages(channel_id, after_ts=last_ts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Poll failed for channel %s: %s", channel_id, exc)
        return

    for msg in messages:
        text: str = msg.get("text", "").strip()
        ts: str = msg.get("timestamp", "")
        if not text:
            session["last_ts"] = ts
            continue

        logger.info("Channel %s — user: %s", channel_id, text[:120])

        try:
            reply = await _call_jira_chat(text, token)
            reply_ts = await _send_reply(channel_id, reply)
            # Advance the cursor past our own reply so we don't re-process it.
            session["last_ts"] = reply_ts or ts
            logger.info("Channel %s — reply sent", channel_id)
        except httpx.HTTPStatusError as exc:
            _http_401 = 401
            if exc.response.status_code == _http_401:
                logger.exception(
                    "Channel %s — token rejected (401). User must re-authenticate.",
                    channel_id,
                )
                # Remove the session so we don't keep hammering with a bad token.
                _sessions.pop(channel_id, None)
                return
            logger.exception("Channel %s — HTTP error", channel_id)
            session["last_ts"] = ts
        except Exception:
            logger.exception("Channel %s — unexpected error", channel_id)
            session["last_ts"] = ts


async def _poll_loop() -> None:
    """Background task: poll all registered channels on a fixed interval."""
    while True:
        for channel_id, session in list(_sessions.items()):
            await _poll_channel(channel_id, session)
        await asyncio.sleep(_poll_interval())


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[type-arg]
    """Start the background poll loop on startup and cancel it on shutdown."""
    task = asyncio.create_task(_poll_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Jira Chat Bridge",
    description=(
        "Polls Team 9's chat service for new messages, forwards them to the "
        "Jira AI /chat endpoint, and posts replies back — one session per "
        "authenticated user."
    ),
    lifespan=lifespan,
    root_path="/prod",
)


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def register_session(body: RegisterSessionRequest) -> dict[str, str]:
    """Register a user session after they complete Jira OAuth2.

    The website calls this endpoint once the user has authenticated.
    The bridge will then monitor the given channel and use the provided
    Atlassian access token for all /chat calls on that channel.
    """
    _sessions[body.channel_id] = {"token": body.token, "last_ts": None}
    logger.info("Session registered for channel %s", body.channel_id)
    return {"status": "registered", "channel_id": body.channel_id}


@app.delete("/sessions/{channel_id}")
def deregister_session(channel_id: str) -> dict[str, str]:
    """Deregister a user session on logout."""
    if channel_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    del _sessions[channel_id]
    logger.info("Session deregistered for channel %s", channel_id)
    return {"status": "deregistered", "channel_id": channel_id}


@app.get("/health")
def health() -> dict[str, Any]:
    """Health check — also reports how many channels are being monitored."""
    return {"status": "ok", "monitored_channels": len(_sessions)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
