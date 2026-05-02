"""Unit tests for MockChatClient — verifies per-user isolation and all CRUD ops."""

from __future__ import annotations

import pytest

from chat_to_issues_integration.chat_client import ChannelNotFoundError, MessageNotFoundError
from chat_to_issues_integration.mock_chat_client import MockChatClient


@pytest.fixture
def client() -> MockChatClient:
    """A fresh MockChatClient for user 'alice'."""
    return MockChatClient(user_id="alice")


@pytest.fixture
def client_with_channel(client: MockChatClient) -> tuple[MockChatClient, str]:
    """Client pre-seeded with one channel; returns (client, channel_id)."""
    ch = client.add_channel("general")
    return client, ch.id


class TestChannels:
    def test_add_and_get_channel(self, client: MockChatClient) -> None:
        ch = client.add_channel("general")
        result = client.get_channel(ch.id)
        assert result.id == ch.id
        assert result.name == "general"

    def test_get_channels_returns_all(self, client: MockChatClient) -> None:
        client.add_channel("general")
        client.add_channel("random")
        assert len(client.get_channels()) == 2

    def test_get_channel_not_found(self, client: MockChatClient) -> None:
        with pytest.raises(ChannelNotFoundError):
            client.get_channel("nonexistent")

    def test_user_isolation(self) -> None:
        alice = MockChatClient(user_id="alice")
        bob = MockChatClient(user_id="bob")
        alice.add_channel("alice-only")
        assert len(bob.get_channels()) == 0


class TestMessages:
    def test_send_and_get_message(self, client_with_channel: tuple[MockChatClient, str]) -> None:
        client, cid = client_with_channel
        msg = client.send_message(cid, "hello world")
        result = client.get_message(msg.id)
        assert result.text == "hello world"
        assert result.channel_id == cid
        assert result.sender == "alice"

    def test_get_messages_newest_first(self, client_with_channel: tuple[MockChatClient, str]) -> None:
        client, cid = client_with_channel
        client.send_message(cid, "first")
        client.send_message(cid, "second")
        msgs = client.get_messages(cid)
        assert msgs[0].text == "second"
        assert msgs[1].text == "first"

    def test_get_messages_respects_limit(self, client_with_channel: tuple[MockChatClient, str]) -> None:
        client, cid = client_with_channel
        for i in range(5):
            client.send_message(cid, f"msg {i}")
        assert len(client.get_messages(cid, limit=3)) == 3

    def test_send_to_unknown_channel_raises(self, client: MockChatClient) -> None:
        with pytest.raises(ChannelNotFoundError):
            client.send_message("bad-channel", "oops")

    def test_get_message_not_found(self, client: MockChatClient) -> None:
        with pytest.raises(MessageNotFoundError):
            client.get_message("nonexistent")

    def test_delete_message(self, client_with_channel: tuple[MockChatClient, str]) -> None:
        client, cid = client_with_channel
        msg = client.send_message(cid, "to delete")
        client.delete_message(msg.id)
        with pytest.raises(MessageNotFoundError):
            client.get_message(msg.id)
        assert all(m.id != msg.id for m in client.get_messages(cid))

    def test_delete_nonexistent_message_raises(self, client: MockChatClient) -> None:
        with pytest.raises(MessageNotFoundError):
            client.delete_message("ghost")

    def test_message_isolation_between_users(self) -> None:
        alice = MockChatClient(user_id="alice")
        bob = MockChatClient(user_id="bob")
        ch_alice = alice.add_channel("shared-name")
        alice.send_message(ch_alice.id, "alice's secret")
        # bob has no channels and cannot see alice's messages
        assert len(bob.get_channels()) == 0
