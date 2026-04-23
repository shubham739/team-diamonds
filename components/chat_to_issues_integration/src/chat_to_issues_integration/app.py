"""IntegrationApp — wires the issue tracker vertical with the chat vertical.

This is the core of the cross-vertical integration. It accepts any
IssueTrackerClient and any ChatClient via dependency injection, so:

  - Jira + Slack  → production
  - Jira + Mock   → local dev / testing
  - Trello + Discord → another team's setup, zero code changes here

Usage example::

    from jira_service_adapter.adapter import get_client as get_tracker_client
    from chat_to_issues_integration.mock_chat_client import MockChatClient
    from chat_to_issues_integration.app import IntegrationApp

    tracker = get_tracker_client()
    chat = MockChatClient(user_id="alice")
    app = IntegrationApp(tracker_client=tracker, chat_client=chat)

    # Post a summary of open issues to a channel
    app.post_issues_to_channel(channel_id="C-general")

    # Create a Jira issue from a chat message
    app.create_issue_from_message(message_id="M-abc123")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.issue import Issue

    from chat_to_issues_integration.chat_client import ChatClient, Message


class IntegrationApp:
    """Bridges an issue tracker and a chat platform for a single user.

    Both clients are injected at construction time, so this class has no
    knowledge of which concrete implementations are in use. Two users each
    get their own IntegrationApp instance — there is no shared state.

    Args:
        tracker_client: Any object implementing the IssueTrackerClient
                        contract (JiraClient, JiraServiceAdapter, etc.).
        chat_client: Any ChatClient implementation (MockChatClient,
                     SlackChatClient, etc.).

    """

    def __init__(self, tracker_client: object, chat_client: ChatClient) -> None:
        """Initialise with injected tracker and chat clients."""
        self._tracker = tracker_client
        self._chat = chat_client

    # ------------------------------------------------------------------
    # Issue tracker → Chat
    # ------------------------------------------------------------------

    def post_issues_to_channel(
        self,
        channel_id: str,
        *,
        max_results: int = 10,
    ) -> list[Message]:
        """Fetch recent issues and post a summary to a chat channel.

        Each issue becomes one message in the channel.

        Args:
            channel_id: The channel to post summaries to.
            max_results: How many issues to fetch and post.

        Returns:
            The list of Message instances that were posted.

        """
        issues: list[Issue] = list(self._tracker.get_issues(max_results=max_results))  # type: ignore[attr-defined]
        posted: list[Message] = []
        for issue in issues:
            text = _format_issue(issue)
            message = self._chat.send_message(channel_id, text)
            posted.append(message)
        return posted

    def post_issue_to_channel(self, issue_id: str, channel_id: str) -> Message:
        """Fetch a single issue and post it to a chat channel.

        Args:
            issue_id: The issue identifier to look up.
            channel_id: The channel to post to.

        Returns:
            The posted Message.

        """
        issue: Issue = self._tracker.get_issue(issue_id)  # type: ignore[attr-defined]
        text = _format_issue(issue)
        return self._chat.send_message(channel_id, text)

    # ------------------------------------------------------------------
    # Chat → Issue tracker
    # ------------------------------------------------------------------

    def create_issue_from_message(self, message_id: str) -> Issue:
        """Create a new issue using the text of a chat message as the title.

        Args:
            message_id: The ID of the message to turn into an issue.

        Returns:
            The newly created Issue.

        """
        message = self._chat.get_message(message_id)
        issue: Issue = self._tracker.create_issue(title=message.text)  # type: ignore[attr-defined]
        return issue

    def create_issue_from_channel_latest(self, channel_id: str) -> Issue:
        """Create an issue from the most recent message in a channel.

        Args:
            channel_id: The channel to read the latest message from.

        Returns:
            The newly created Issue.

        """
        messages = self._chat.get_messages(channel_id, limit=1)
        if not messages:
            msg = f"No messages found in channel '{channel_id}'"
            raise ValueError(msg)
        return self.create_issue_from_message(messages[0].id)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def list_channels(self) -> list[str]:
        """Return the names of all channels visible to the chat client.

        Returns:
            A list of channel name strings.

        """
        return [ch.name for ch in self._chat.get_channels()]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_issue(issue: Issue) -> str:  # type: ignore[name-defined]
    """Render an Issue as a human-readable chat message string."""
    due = f" | due: {issue.due_date}" if issue.due_date else ""  # type: ignore[attr-defined]
    return f"[{issue.status}] {issue.id}: {issue.title}{due}"  # type: ignore[attr-defined]
