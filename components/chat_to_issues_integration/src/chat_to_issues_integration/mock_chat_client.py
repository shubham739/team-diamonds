"""In-memory mock implementation of ChatClient.

Used for local development and testing before a real Slack (or other chat
platform) client is wired in. Each instance maintains its own isolated
state — instantiate one per user to guarantee no cross-user data leakage.

Swap this out for a real ChatClient implementation (e.g. SlackChatClient)
without changing any IntegrationApp logic.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from chat_to_issues_integration.chat_client import (
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
    MessageNotFoundError,
)


class MockChatClient(ChatClient):
    """Fully in-memory ChatClient for local development and testing.

    State is scoped to this instance — two MockChatClient instances never
    share channels or messages, ensuring per-user isolation.

    Args:
        user_id: An identifier for the owning user. Used only for
                 traceability (e.g. sender field on messages).

    """

    def __init__(self, user_id: str = "mock-user") -> None:
        """Initialise with an empty channel and message store."""
        self._user_id = user_id
        # channel_id -> Channel
        self._channels: dict[str, Channel] = {}
        # channel_id -> list[Message] (insertion order = chronological)
        self._messages: dict[str, list[Message]] = defaultdict(list)
        # message_id -> Message (for fast lookup)
        self._message_index: dict[str, Message] = {}

    # ------------------------------------------------------------------
    # Seed helpers — useful in tests and local demos
    # ------------------------------------------------------------------

    def add_channel(self, name: str, channel_id: str | None = None) -> Channel:
        """Create a channel in the mock store and return it.

        Args:
            name: Human-readable channel name.
            channel_id: Optional explicit ID; auto-generated if omitted.

        Returns:
            The created Channel.

        """
        cid = channel_id or f"C-{uuid.uuid4().hex[:8]}"
        channel = Channel(id=cid, name=name)
        self._channels[cid] = channel
        return channel

    # ------------------------------------------------------------------
    # ChatClient contract
    # ------------------------------------------------------------------

    def get_channels(self) -> list[Channel]:
        """Return all channels in this mock instance."""
        return list(self._channels.values())

    def get_channel(self, channel_id: str) -> Channel:
        """Return a channel by ID.

        Raises:
            ChannelNotFoundError: If the channel does not exist.

        """
        if channel_id not in self._channels:
            msg = f"Channel '{channel_id}' not found"
            raise ChannelNotFoundError(msg)
        return self._channels[channel_id]

    def get_messages(self, channel_id: str, limit: int = 20) -> list[Message]:
        """Return the most recent messages from a channel, newest first.

        Raises:
            ChannelNotFoundError: If the channel does not exist.

        """
        self.get_channel(channel_id)  # validates channel exists
        msgs = self._messages[channel_id]
        return list(reversed(msgs[-limit:]))

    def get_message(self, message_id: str) -> Message:
        """Return a message by ID.

        Raises:
            MessageNotFoundError: If the message does not exist.

        """
        if message_id not in self._message_index:
            msg = f"Message '{message_id}' not found"
            raise MessageNotFoundError(msg)
        return self._message_index[message_id]

    def send_message(self, channel_id: str, message_text: str) -> Message:
        """Append a message to a channel and return it.

        Raises:
            ChannelNotFoundError: If the channel does not exist.

        """
        self.get_channel(channel_id)  # validates channel exists
        mid = f"M-{uuid.uuid4().hex[:8]}"
        message = Message(
            id=mid,
            channel_id=channel_id,
            text=message_text,
            sender=self._user_id,
        )
        self._messages[channel_id].append(message)
        self._message_index[mid] = message
        return message

    def delete_message(self, message_id: str) -> None:
        """Remove a message from the store.

        Raises:
            MessageNotFoundError: If the message does not exist.

        """
        message = self.get_message(message_id)  # raises if not found
        self._messages[message.channel_id] = [
            m for m in self._messages[message.channel_id] if m.id != message_id
        ]
        del self._message_index[message_id]
