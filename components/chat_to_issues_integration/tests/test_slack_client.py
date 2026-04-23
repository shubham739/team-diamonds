"""Tests for SlackChatClient."""

import os
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from chat_to_issues_integration.chat_client import ChannelNotFoundError, MessageNotFoundError
from chat_to_issues_integration.slack_client import SlackChatClient


class TestSlackChatClient:
    """Test SlackChatClient implementation."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        client = SlackChatClient(token="xoxb-test-token")
        assert client._token == "xoxb-test-token"

    def test_init_with_env_token(self):
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-env-token"}):
            client = SlackChatClient()
            assert client._token == "xoxb-env-token"

    def test_init_no_token_raises_error(self):
        """Test initialization without token raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack token required"):
                SlackChatClient()

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_channels_success(self, mock_web_client):
        """Test successful channel listing."""
        # Mock Slack API response
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "channels": [
                {"id": "C123", "name": "general"},
                {"id": "C456", "name": "random"},
            ],
        }

        client = SlackChatClient(token="xoxb-test")
        channels = client.get_channels()

        assert len(channels) == 2
        assert channels[0].id == "C123"
        assert channels[0].name == "general"
        assert channels[1].id == "C456"
        assert channels[1].name == "random"
        mock_client.conversations_list.assert_called_once_with(types="public_channel")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_channels_api_error(self, mock_web_client):
        """Test channel listing with API error."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_list.side_effect = SlackApiError(
            message="API error", response={"error": "invalid_auth"},
        )

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(ChannelNotFoundError, match="Failed to list channels"):
            client.get_channels()

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_channel_success(self, mock_web_client):
        """Test successful single channel retrieval."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_info.return_value = {
            "channel": {"id": "C123", "name": "general"},
        }

        client = SlackChatClient(token="xoxb-test")
        channel = client.get_channel("C123")

        assert channel.id == "C123"
        assert channel.name == "general"
        mock_client.conversations_info.assert_called_once_with(channel="C123")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_channel_not_found(self, mock_web_client):
        """Test channel not found error."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_info.side_effect = SlackApiError(
            message="Channel not found", response={"error": "channel_not_found"},
        )

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(ChannelNotFoundError, match="Channel 'C123' not found"):
            client.get_channel("C123")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_messages_success(self, mock_web_client):
        """Test successful message retrieval."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_history.return_value = {
            "messages": [
                {"ts": "1234567890.123456", "text": "Hello", "user": "U123"},
                {"ts": "1234567891.123456", "text": "World", "user": "U456"},
            ],
        }

        client = SlackChatClient(token="xoxb-test")
        messages = client.get_messages("C123", limit=10)

        assert len(messages) == 2
        assert messages[0].id == "1234567890.123456"
        assert messages[0].text == "Hello"
        assert messages[0].sender == "U123"
        assert messages[0].channel_id == "C123"
        mock_client.conversations_history.assert_called_once_with(channel="C123", limit=10)

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_messages_channel_not_found(self, mock_web_client):
        """Test message retrieval with channel not found."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_history.side_effect = SlackApiError(
            message="Channel not found", response={"error": "channel_not_found"},
        )

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(ChannelNotFoundError, match="Channel 'C123' not found"):
            client.get_messages("C123")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_message_success(self, mock_web_client):
        """Test successful single message retrieval."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_history.return_value = {
            "messages": [
                {"ts": "1234567890.123456", "text": "Hello", "user": "U123"},
            ],
        }

        client = SlackChatClient(token="xoxb-test")
        message = client.get_message("C123:1234567890.123456")

        assert message.id == "1234567890.123456"
        assert message.text == "Hello"
        assert message.sender == "U123"
        assert message.channel_id == "C123"

    def test_get_message_invalid_format(self):
        """Test get_message with invalid message ID format."""
        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(MessageNotFoundError, match="Invalid message_id format"):
            client.get_message("invalid-format")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_get_message_not_found(self, mock_web_client):
        """Test get_message when message is not found."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.conversations_history.return_value = {"messages": []}

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(MessageNotFoundError, match="Message 'C123:1234567890.123456' not found"):
            client.get_message("C123:1234567890.123456")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_send_message_success(self, mock_web_client):
        """Test successful message sending."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.chat_postMessage.return_value = {
            "ts": "1234567890.123456",
            "message": {"user": "U123"},
        }

        client = SlackChatClient(token="xoxb-test")
        message = client.send_message("C123", "Hello World")

        assert message.id == "1234567890.123456"
        assert message.text == "Hello World"
        assert message.channel_id == "C123"
        assert message.sender == "U123"
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C123", text="Hello World",
        )

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_send_message_channel_not_found(self, mock_web_client):
        """Test send_message with channel not found."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.chat_postMessage.side_effect = SlackApiError(
            message="Channel not found", response={"error": "channel_not_found"},
        )

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(ChannelNotFoundError, match="Channel 'C123' not found"):
            client.send_message("C123", "Hello")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_delete_message_success(self, mock_web_client):
        """Test successful message deletion."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client

        client = SlackChatClient(token="xoxb-test")
        client.delete_message("C123:1234567890.123456")

        mock_client.chat_delete.assert_called_once_with(
            channel="C123", ts="1234567890.123456",
        )

    def test_delete_message_invalid_format(self):
        """Test delete_message with invalid message ID format."""
        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(MessageNotFoundError, match="Invalid message_id format"):
            client.delete_message("invalid-format")

    @patch("chat_to_issues_integration.slack_client.WebClient")
    def test_delete_message_not_found(self, mock_web_client):
        """Test delete_message when message is not found."""
        mock_client = MagicMock()
        mock_web_client.return_value = mock_client
        mock_client.chat_delete.side_effect = SlackApiError(
            message="Message not found", response={"error": "message_not_found"},
        )

        client = SlackChatClient(token="xoxb-test")
        with pytest.raises(MessageNotFoundError, match="Message 'C123:1234567890.123456' not found"):
            client.delete_message("C123:1234567890.123456")

    def test_get_client_factory_function(self):
        """Test the get_client factory function."""
        from chat_to_issues_integration.slack_client import get_client

        client = get_client(token="xoxb-test")
        assert isinstance(client, SlackChatClient)
        assert client._token == "xoxb-test"

    def test_get_client_factory_no_token(self):
        """Test get_client factory without token."""
        from chat_to_issues_integration.slack_client import get_client

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack token required"):
                get_client()
