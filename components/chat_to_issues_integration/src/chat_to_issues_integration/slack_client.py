"""Slack implementation of ChatClient using slack-sdk."""

from __future__ import annotations

import os
from typing import Any, cast

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from chat_to_issues_integration.chat_client import (
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
    MessageNotFoundError,
)


class SlackChatClient(ChatClient):
    """Concrete Slack implementation of ChatClient.

    Uses the Slack Web API via slack-sdk. Each instance is scoped to a single
    user's Slack token, ensuring per-user isolation.

    Args:
        token: Slack Bot User OAuth Token (starts with xoxb-).

    Environment variables (alternative to passing token):
        SLACK_BOT_TOKEN: Bot token for authentication.

    """

    def __init__(self, token: str | None = None) -> None:
        """Initialise with a Slack bot token."""
        self._token = token or os.environ.get("SLACK_BOT_TOKEN", "")
        if not self._token:
            msg = "Slack token required: pass token= or set SLACK_BOT_TOKEN"
            raise ValueError(msg)
        self._client = WebClient(token=self._token)

    def get_channels(self) -> list[Channel]:
        """Return all public channels visible to the bot."""
        try:
            response = self._client.conversations_list(types="public_channel")
            channels: list[Any] = response.get("channels", [])
            return [
                Channel(id=ch["id"], name=ch["name"])
                for ch in channels
                if isinstance(ch, dict)
            ]
        except SlackApiError as e:
            msg = f"Failed to list channels: {e.response['error']}"
            raise ChannelNotFoundError(msg) from e

    def get_channel(self, channel_id: str) -> Channel:
        """Return a single channel by ID."""
        try:
            response = self._client.conversations_info(channel=channel_id)
            ch = response["channel"]
            return Channel(id=ch["id"], name=ch["name"])
        except SlackApiError as e:
            if e.response["error"] == "channel_not_found":
                msg = f"Channel '{channel_id}' not found"
                raise ChannelNotFoundError(msg) from e
            raise

    def get_messages(self, channel_id: str, limit: int = 20) -> list[Message]:
        """Fetch recent messages from a channel, newest first."""
        try:
            response = self._client.conversations_history(
                channel=channel_id,
                limit=limit,
            )
            messages: list[Any] = response.get("messages", [])
            return [
                Message(
                    id=msg["ts"],  # Slack uses timestamp as message ID
                    channel_id=channel_id,
                    text=msg.get("text", ""),
                    sender=msg.get("user"),
                )
                for msg in messages
                if isinstance(msg, dict)
            ]
        except SlackApiError as e:
            if e.response["error"] == "channel_not_found":
                msg = f"Channel '{channel_id}' not found"
                raise ChannelNotFoundError(msg) from e
            raise

    def get_message(self, message_id: str) -> Message:
        """Fetch a single message by ID.

        Note: Slack doesn't have a direct "get message by ID" API.
        This implementation searches recent messages, which may not scale.
        For production, consider caching or a different approach.

        """
        # message_id format: "channel_id:timestamp"
        if ":" not in message_id:
            msg = f"Invalid message_id format: {message_id} (expected 'channel_id:timestamp')"
            raise MessageNotFoundError(msg)

        channel_id, ts = message_id.split(":", 1)
        messages = self.get_messages(channel_id, limit=100)
        for message in messages:
            if message.id == ts:
                return message

        err = f"Message '{message_id}' not found"
        raise MessageNotFoundError(err)

    def send_message(self, channel_id: str, message_text: str) -> Message:
        """Post a message to a channel."""
        try:
            response = self._client.chat_postMessage(
                channel=channel_id,
                text=message_text,
            )
            msg_data = cast("dict[str, Any]", response.get("message") or {})
            return Message(
                id=response["ts"],
                channel_id=channel_id,
                text=message_text,
                sender=msg_data.get("user"),
            )
        except SlackApiError as e:
            if e.response["error"] == "channel_not_found":
                msg = f"Channel '{channel_id}' not found"
                raise ChannelNotFoundError(msg) from e
            raise

    def delete_message(self, message_id: str) -> None:
        """Delete a message.

        Args:
            message_id: Format must be "channel_id:timestamp".

        """
        if ":" not in message_id:
            msg = f"Invalid message_id format: {message_id} (expected 'channel_id:timestamp')"
            raise MessageNotFoundError(msg)

        channel_id, ts = message_id.split(":", 1)
        try:
            self._client.chat_delete(channel=channel_id, ts=ts)
        except SlackApiError as e:
            if e.response["error"] in ("message_not_found", "channel_not_found"):
                msg = f"Message '{message_id}' not found"
                raise MessageNotFoundError(msg) from e
            raise


def get_client(token: str | None = None) -> SlackChatClient:
    """Create a SlackChatClient.

    Args:
        token: Slack Bot User OAuth Token. If not provided, reads from
               SLACK_BOT_TOKEN environment variable.

    Returns:
        A configured SlackChatClient.

    Raises:
        ValueError: If no token is provided and SLACK_BOT_TOKEN is not set.

    """
    return SlackChatClient(token=token)
