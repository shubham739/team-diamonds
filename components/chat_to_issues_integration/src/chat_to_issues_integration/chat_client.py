"""Abstract chat client interface.

This ABC defines the shared contract for any chat platform (Slack, Discord,
Telegram). The interface mirrors the suggested API from the HW3 spec for
Chat teams.

When a real shared ospd-chat-api package is published by the chat vertical,
this file can be replaced with a direct import from that package — the rest
of the integration code remains unchanged because it only depends on this ABC.

Suggested interface from HW3 spec:
    get_messages(channel_id, limit) -> list[Message]
    get_message(message_id)         -> Message
    send_message(channel_id, text)  -> Message
    delete_message(message_id)      -> None
    get_channels()                  -> list[Channel]
    get_channel(channel_id)         -> Channel
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Channel:
    """Represents a chat channel."""

    id: str
    name: str


@dataclass
class Message:
    """Represents a single chat message."""

    id: str
    channel_id: str
    text: str
    sender: str | None = field(default=None)


class ChannelNotFoundError(Exception):
    """Raised when a channel cannot be found."""


class MessageNotFoundError(Exception):
    """Raised when a message cannot be found."""


class ChatClient(ABC):
    """Abstract base class for a chat platform client.

    Any chat vertical implementation (Slack, Discord, Telegram) must
    subclass this and implement all abstract methods.

    Each instance is scoped to a single user — instantiate one per user
    to ensure full isolation between users.
    """

    @abstractmethod
    def get_channels(self) -> list[Channel]:
        """Return all channels visible to this user.

        Returns:
            A list of Channel instances.

        """
        raise NotImplementedError

    @abstractmethod
    def get_channel(self, channel_id: str) -> Channel:
        """Return a single channel by ID.

        Args:
            channel_id: The platform-specific channel identifier.

        Returns:
            The corresponding Channel instance.

        Raises:
            ChannelNotFoundError: If no channel with that ID exists.

        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, limit: int = 20) -> list[Message]:
        """Fetch recent messages from a channel.

        Args:
            channel_id: The channel to read from.
            limit: Maximum number of messages to return.

        Returns:
            A list of Message instances, newest first.

        """
        raise NotImplementedError

    @abstractmethod
    def get_message(self, message_id: str) -> Message:
        """Fetch a single message by ID.

        Args:
            message_id: The platform-specific message identifier.

        Returns:
            The corresponding Message instance.

        Raises:
            MessageNotFoundError: If no message with that ID exists.

        """
        raise NotImplementedError

    @abstractmethod
    def send_message(self, channel_id: str, message_text: str) -> Message:
        """Post a message to a channel.

        Args:
            channel_id: The channel to post to.
            message_text: The text content of the message.

        Returns:
            The posted Message instance.

        Raises:
            ChannelNotFoundError: If the channel does not exist.

        """
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, message_id: str) -> None:
        """Delete a message.

        Args:
            message_id: The platform-specific message identifier.

        Raises:
            MessageNotFoundError: If no message with that ID exists.

        """
        raise NotImplementedError
