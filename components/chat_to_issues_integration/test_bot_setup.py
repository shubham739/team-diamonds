"""Test bot setup and connections."""

import os
import sys

from dotenv import load_dotenv

from chat_to_issues_integration import SlackChatClient
from jira_service_adapter.adapter import get_client as get_tracker_client

# Load environment variables
load_dotenv(".venv/.env")


def test_environment_variables() -> bool:
    """Test that all required environment variables are set."""
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET",
        "JIRA_SERVICE_BASE_URL",
        "JIRA_SERVICE_ACCESS_TOKEN",
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)

    return len(missing) == 0


def test_slack_connection() -> bool:
    """Test Slack API connection."""
    try:
        client = SlackChatClient()
        channels = client.get_channels()
        return len(channels) >= 0  # Even 0 channels is a successful connection
    except Exception:
        return False


def test_jira_connection() -> bool:
    """Test Jira service connection."""
    try:
        client = get_tracker_client()
        list(client.get_issues(max_results=1))  # Try to get at least one issue
        return True
    except Exception:
        return False


def main() -> None:
    """Run all tests."""
    env_ok = test_environment_variables()
    slack_ok = test_slack_connection() if env_ok else False
    jira_ok = test_jira_connection() if env_ok else False

    # Return exit code based on results
    if env_ok and slack_ok and jira_ok:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()
