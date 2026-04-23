"""Unit tests for IntegrationApp — uses MockChatClient and a mock tracker."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chat_to_issues_integration.app import IntegrationApp
from chat_to_issues_integration.mock_chat_client import MockChatClient


def _make_issue(issue_id: str, title: str, status: str = "to_do", due_date: str | None = None) -> MagicMock:
    """Build a mock Issue with the given fields."""
    issue: MagicMock = MagicMock()
    issue.id = issue_id
    issue.title = title
    issue.status = status
    issue.due_date = due_date
    return issue


@pytest.fixture
def chat() -> MockChatClient:
    return MockChatClient(user_id="alice")


@pytest.fixture
def tracker() -> MagicMock:
    return MagicMock()


@pytest.fixture
def app(tracker: MagicMock, chat: MockChatClient) -> IntegrationApp:
    return IntegrationApp(tracker_client=tracker, chat_client=chat)


class TestPostIssuesToChannel:
    def test_posts_one_message_per_issue(self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient) -> None:
        ch = chat.add_channel("general")
        tracker.get_issues.return_value = [
            _make_issue("PROJ-1", "Fix login bug"),
            _make_issue("PROJ-2", "Add dark mode"),
        ]
        posted = app.post_issues_to_channel(ch.id, max_results=2)
        assert len(posted) == 2
        assert len(chat.get_messages(ch.id)) == 2

    def test_message_contains_issue_id_and_title(
        self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient,
    ) -> None:
        ch = chat.add_channel("general")
        tracker.get_issues.return_value = [_make_issue("PROJ-1", "Fix login bug", due_date="2026-05-01")]
        posted = app.post_issues_to_channel(ch.id)
        assert "PROJ-1" in posted[0].text
        assert "Fix login bug" in posted[0].text
        assert "2026-05-01" in posted[0].text

    def test_no_issues_posts_nothing(self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient) -> None:
        ch = chat.add_channel("general")
        tracker.get_issues.return_value = []
        posted = app.post_issues_to_channel(ch.id)
        assert posted == []


class TestPostSingleIssue:
    def test_post_issue_to_channel(self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient) -> None:
        ch = chat.add_channel("general")
        tracker.get_issue.return_value = _make_issue("PROJ-5", "Deploy to prod")
        msg = app.post_issue_to_channel("PROJ-5", ch.id)
        assert "PROJ-5" in msg.text
        tracker.get_issue.assert_called_once_with("PROJ-5")


class TestCreateIssueFromMessage:
    def test_creates_issue_with_message_text_as_title(
        self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient,
    ) -> None:
        ch = chat.add_channel("requests")
        msg = chat.send_message(ch.id, "Please add export to CSV")
        tracker.create_issue.return_value = _make_issue("PROJ-99", "Please add export to CSV")
        issue = app.create_issue_from_message(msg.id)
        tracker.create_issue.assert_called_once_with(title="Please add export to CSV")
        assert issue.title == "Please add export to CSV"

    def test_create_from_latest_message(self, app: IntegrationApp, tracker: MagicMock, chat: MockChatClient) -> None:
        ch = chat.add_channel("requests")
        chat.send_message(ch.id, "old message")
        chat.send_message(ch.id, "latest request")
        tracker.create_issue.return_value = _make_issue("PROJ-100", "latest request")
        issue = app.create_issue_from_channel_latest(ch.id)
        tracker.create_issue.assert_called_once_with(title="latest request")
        assert issue.id == "PROJ-100"

    def test_create_from_empty_channel_raises(
        self, app: IntegrationApp, chat: MockChatClient,
    ) -> None:
        ch = chat.add_channel("empty")
        with pytest.raises(ValueError, match="No messages"):
            app.create_issue_from_channel_latest(ch.id)


class TestListChannels:
    def test_returns_channel_names(self, app: IntegrationApp, chat: MockChatClient) -> None:
        chat.add_channel("general")
        chat.add_channel("random")
        names = app.list_channels()
        assert "general" in names
        assert "random" in names
