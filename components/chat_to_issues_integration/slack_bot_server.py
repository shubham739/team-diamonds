"""Slack Bot Server with App Mentions for Cross-Vertical Integration.

This creates an interactive Slack bot that responds to @mentions with commands:
- @bot create issue: <description> - Create a Jira issue
- @bot list issues - Show recent Jira issues
- @bot post issues - Post issues to current channel
- @bot help - Show available commands

Prerequisites:
1. SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET in .venv/.env
2. Jira service credentials in .venv/.env
3. Bot invited to channels where you want to use it
4. Slack app configured with Event Subscriptions pointing to this server

Run with:
    .venv/Scripts/python.exe components/chat_to_issues_integration/slack_bot_server.py
"""

import hashlib
import hmac
import json
import os
import re
import time
from typing import Any, cast

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from chat_to_issues_integration import IntegrationApp, SlackChatClient
from jira_service_adapter.adapter import get_client as get_tracker_client

# Load environment variables
load_dotenv(".venv/.env")

app = FastAPI(title="Slack Bot Server", description="Cross-vertical integration bot")

# Global integration app (in production, this would be per-user)
integration_app: IntegrationApp | None = None

# Event deduplication - store recent event IDs to prevent duplicates
processed_events: set[str] = set()

# Constants
TIMESTAMP_TOLERANCE = 300  # 5 minutes in seconds
MAX_PROCESSED_EVENTS = 100


def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify that the request came from Slack."""
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        return False

    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"

    # Create the expected signature
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)


def initialize_integration() -> IntegrationApp:
    """Initialize the integration app with Slack and Jira clients."""
    # Check required environment variables
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET",
        "JIRA_SERVICE_BASE_URL",
        "JIRA_SERVICE_ACCESS_TOKEN",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        missing_vars = ", ".join(missing)
        msg = f"Missing required environment variables: {missing_vars}"
        raise ValueError(msg)

    # Initialize clients
    chat_client = SlackChatClient()
    tracker_client = get_tracker_client()

    return IntegrationApp(tracker_client=tracker_client, chat_client=chat_client)


def parse_mention_command(text: str, bot_user_id: str) -> tuple[str, str]:
    """Parse a mention command and extract the action and parameters.

    Args:
        text: The message text from Slack
        bot_user_id: The bot's user ID to remove from mentions

    Returns:
        Tuple of (command, parameters)

    """
    # Remove the bot mention and clean up the text
    mention_pattern = f"<@{bot_user_id}>"
    clean_text = text.replace(mention_pattern, "").strip()

    # Parse commands
    if clean_text.lower().startswith("create issue:"):
        return "create_issue", clean_text[13:].strip()
    if clean_text.lower() in ["list issues", "list"]:
        return "list_issues", ""
    if clean_text.lower() in ["post issues", "post"]:
        return "post_issues", ""
    if clean_text.lower() in ["help", "?"]:
        return "help", ""
    return "unknown", clean_text


async def handle_create_issue(_channel_id: str, description: str) -> str:
    """Create a Jira issue and return a response message."""
    if not description:
        return "❌ Please provide a description. Usage: `@diamond create issue: Your issue description`"

    try:
        # Create issue via integration app
        assert integration_app is not None
        tracker = cast("Any", integration_app._tracker)  # noqa: SLF001
        issue = tracker.create_issue(
            title=description[:100],  # Limit title length
            desc=f"Created from Slack channel.\n\nDescription: {description}",
        )
    except Exception as e:  # noqa: BLE001
        return f"❌ Failed to create issue: {e!s}"
    else:
        return f"✅ **Issue Created!**\n**ID:** {issue.id}\n**Title:** {issue.title}\n**Status:** {issue.status}"


async def handle_list_issues(_channel_id: str) -> str:
    """List recent Jira issues and return a response message."""
    try:
        assert integration_app is not None
        tracker = cast("Any", integration_app._tracker)  # noqa: SLF001
        issues = list(tracker.get_issues(max_results=5))

        if not issues:
            return "📋 No issues found in Jira."

        response = "📋 **Recent Issues:**\n"
        for i, issue in enumerate(issues, 1):
            response += f"{i}. **{issue.id}** - {issue.title} ({issue.status})\n"
    except Exception as e:  # noqa: BLE001
        return f"❌ Failed to list issues: {e!s}"
    else:
        return response


async def handle_post_issues(channel_id: str) -> str:
    """Post issues to the current channel and return a response message."""
    try:
        assert integration_app is not None
        posted_messages = integration_app.post_issues_to_channel(channel_id, max_results=3)

        if not posted_messages:
            return "📋 No issues to post (Jira might be empty)."

        return f"✅ Posted {len(posted_messages)} issues to this channel!"

    except Exception as e:  # noqa: BLE001
        return f"❌ Failed to post issues: {e!s}"


def get_help_message() -> str:
    """Return the help message with available commands."""
    return """🤖 **Slack-Jira Integration Bot**

**Available Commands:**
• `@diamond create issue: <description>` - Create a new Jira issue
• `@diamond list issues` - Show recent Jira issues
• `@diamond post issues` - Post issues to this channel
• `@diamond help` - Show this help message

**Examples:**
• `@diamond create issue: Fix login button not working`
• `@diamond list issues`
• `@diamond post issues`"""


def _verify_request(body: bytes, headers: dict[str, str]) -> None:
    """Verify the Slack request is authentic."""
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")

    # Check timestamp to prevent replay attacks
    if abs(time.time() - int(timestamp)) > TIMESTAMP_TOLERANCE:
        raise HTTPException(status_code=400, detail="Request timestamp too old")

    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")


def _parse_request_body(body: bytes) -> dict[str, Any]:
    """Parse the JSON payload from Slack."""
    try:
        data: dict[str, Any] = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    else:
        return data


def _is_duplicate_event(event_id: str) -> bool:
    """Check if this event has already been processed."""
    if event_id in processed_events:
        return True

    # Add to processed events (keep only last N to prevent memory issues)
    processed_events.add(event_id)
    if len(processed_events) > MAX_PROCESSED_EVENTS:
        processed_events.clear()

    return False


def _ensure_integration_initialized() -> None:
    """Initialize the integration app if not already done."""
    global integration_app  # noqa: PLW0603
    if integration_app is None:
        try:
            integration_app = initialize_integration()
        except Exception as e:
            msg = f"Failed to initialize integration: {e}"
            raise HTTPException(status_code=500, detail=msg) from e


async def _handle_app_mention(event: dict[str, Any]) -> JSONResponse:
    """Handle app mention events."""
    # Check for duplicate events
    event_id = f"{event.get('ts')}_{event.get('channel')}_{event.get('user')}"
    if _is_duplicate_event(event_id):
        return JSONResponse({"status": "duplicate_skipped"})

    # Initialize integration if needed
    _ensure_integration_initialized()
    assert integration_app is not None

    # Extract event details
    channel_id: str = event.get("channel") or ""
    text = event.get("text", "")

    # Get bot user ID
    bot_user_id = os.getenv("SLACK_BOT_USER_ID", "U0B0131K97S")
    if not bot_user_id:
        # Try to extract from the mention in the text
        mention_match = re.search(r"<@(\w+)>", text)
        if mention_match:
            bot_user_id = mention_match.group(1)

    # Parse and execute the command
    command, params = parse_mention_command(text, bot_user_id)

    try:
        if command == "create_issue":
            response_text = await handle_create_issue(channel_id, params)
        elif command == "list_issues":
            response_text = await handle_list_issues(channel_id)
        elif command == "post_issues":
            response_text = await handle_post_issues(channel_id)
        elif command == "help":
            response_text = get_help_message()
        else:
            response_text = f"❓ Unknown command. Type `@diamond help` for available commands.\n\nYou said: {params}"

        # Send response back to Slack
        chat_client = integration_app._chat  # noqa: SLF001
        chat_client.send_message(channel_id, response_text)

    except Exception as e:  # noqa: BLE001
        # Send error message to Slack
        error_msg = f"❌ Error processing command: {e!s}"
        try:
            chat_client = integration_app._chat  # noqa: SLF001
            chat_client.send_message(channel_id, error_msg)
        except Exception:  # noqa: BLE001, S110
            pass  # If we can't send error message, just continue

    return JSONResponse({"status": "ok"})


@app.post("/slack/events")
async def slack_events(request: Request) -> JSONResponse:
    """Handle Slack Events API callbacks."""
    # Get request data
    body = await request.body()
    headers = dict(request.headers)

    # Verify the request came from Slack
    _verify_request(body, headers)

    # Parse the JSON payload
    data = _parse_request_body(body)

    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return JSONResponse({"challenge": data.get("challenge")})

    # Handle app mention events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        if event.get("type") == "app_mention":
            return await _handle_app_mention(event)

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "slack-bot-server"}


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with basic info."""
    return {
        "service": "Slack Bot Server",
        "description": "Cross-vertical integration bot for Slack and Jira",
        "endpoints": {
            "events": "/slack/events",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
