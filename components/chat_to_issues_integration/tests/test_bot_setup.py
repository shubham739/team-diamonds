"""Test bot setup and connections."""

import os
import sys

import pytest
from dotenv import load_dotenv

from chat_to_issues_integration import SlackChatClient
from jira_service_adapter.adapter import get_client as get_tracker_client

# Load environment variables
load_dotenv(".venv/.env")

_REQUIRED_ENV_VARS = [
    "SLACK_BOT_TOKEN",
    "SLACK_SIGNING_SECRET",
    "JIRA_SERVICE_BASE_URL",
    "JIRA_SERVICE_ACCESS_TOKEN",
]
_MISSING_ENV_VARS = [name for name in _REQUIRED_ENV_VARS if not os.getenv(name)]

pytestmark = [
    pytest.mark.local_credentials,
    pytest.mark.skipif(
        bool(_MISSING_ENV_VARS),
        reason=f"Missing required environment variables: {', '.join(_MISSING_ENV_VARS)}",
    ),
]


def test_environment_variables() -> None:
    """Test that all required environment variables are set."""
    assert not _MISSING_ENV_VARS, f"Missing required environment variables: {', '.join(_MISSING_ENV_VARS)}"


def test_slack_connection() -> None:
    """Test Slack API connection."""
    client = SlackChatClient()
    channels = client.get_channels()
    assert isinstance(channels, list)


def test_jira_connection() -> None:
    """Test Jira service connection."""
    client = get_tracker_client()
    issues = list(client.get_issues(max_results=1))
    assert isinstance(issues, list)


def main() -> None:
    """Run all tests."""
    try:
        test_environment_variables()
        test_slack_connection()
        test_jira_connection()
    except Exception:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
