"""Tests for the auth module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from jira_service.auth import (
    AuthenticationError,
    TokenRefreshError,
    create_chat_session,
    exchange_code_for_token,
    get_accessible_resources,
    get_authorize_url,
    get_session,
    get_session_by_token,
    get_user_info,
    get_valid_token,
    is_token_expired,
    refresh_access_token,
    store_session,
    update_session_channel,
)


def test_get_authorize_url() -> None:
    with patch("jira_service.auth.JIRA_OAUTH_CLIENT_ID", "test_client_id"):
        url = get_authorize_url("test_state")
    assert "state=test_state" in url
    assert "response_type=code" in url


@patch("requests.post")
def test_exchange_code_for_token_success(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "token123", "refresh_token": "refresh123", "expires_in": 3600}
    mock_post.return_value = mock_resp

    res = exchange_code_for_token("my_code")
    assert res["access_token"] == "token123"


@patch("requests.post")
def test_exchange_code_for_token_failure(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.RequestException("API down")

    with pytest.raises(AuthenticationError):
        exchange_code_for_token("my_code")


@patch("requests.post")
def test_refresh_access_token_success(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "new_token123", "refresh_token": "new_refresh123", "expires_in": 3600}
    mock_post.return_value = mock_resp

    res = refresh_access_token("refresh123")
    assert res["access_token"] == "new_token123"


@patch("requests.post")
def test_refresh_access_token_failure(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.RequestException("API down")

    with pytest.raises(TokenRefreshError):
        refresh_access_token("refresh123")


@patch("requests.get")
def test_get_user_info_success(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"account_id": "user123"}
    mock_get.return_value = mock_resp

    res = get_user_info("my_token")
    assert res["account_id"] == "user123"


@patch("requests.get")
def test_get_user_info_failure(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.RequestException("API down")

    with pytest.raises(AuthenticationError):
        get_user_info("my_token")


def test_session_management() -> None:
    store_session("user99", {"access_token": "val1", "refresh_token": "val2", "expires_in": 3600})
    s = get_session("user99")
    assert s is not None
    assert s["access_token"] == "val1"


def test_is_token_expired() -> None:
    store_session("user88", {"access_token": "val1", "refresh_token": "val2", "expires_in": 0})
    assert is_token_expired("user88") is True

    store_session("user77", {"access_token": "val1", "refresh_token": "val2", "expires_in": 3600})
    assert is_token_expired("user77") is False

    assert is_token_expired("no_such_user") is True


@patch("requests.get")
def test_get_accessible_resources_success(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"id": "cloud-abc", "name": "My Jira"}]
    mock_get.return_value = mock_resp

    resources = get_accessible_resources("my_token")
    assert resources[0]["id"] == "cloud-abc"
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "accessible-resources" in call_args[0][0]
    assert call_args[1]["headers"]["Authorization"] == "Bearer my_token"


@patch("requests.get")
def test_get_accessible_resources_failure(mock_get: MagicMock) -> None:
    import requests
    mock_get.side_effect = requests.RequestException("network error")

    with pytest.raises(AuthenticationError):
        get_accessible_resources("my_token")


def test_store_session_stores_cloud_id() -> None:
    store_session("user_cloud", {"access_token": "tok", "refresh_token": "ref", "expires_in": 3600}, "cloud-xyz")
    session = get_session("user_cloud")
    assert session is not None
    assert session["cloud_id"] == "cloud-xyz"
    assert session["access_token"] == "tok"
    assert session["chat_session_id"] == ""
    assert session["channel_id"] == ""


def test_store_session_defaults_cloud_id_to_empty_string() -> None:
    store_session("user_nocloud", {"access_token": "tok", "refresh_token": "ref", "expires_in": 3600})
    session = get_session("user_nocloud")
    assert session is not None
    assert session["cloud_id"] == ""


def test_store_session_stores_chat_session_id() -> None:
    store_session("user_chat", {"access_token": "tok", "expires_in": 3600}, chat_session_id="sess-abc")
    session = get_session("user_chat")
    assert session is not None
    assert session["chat_session_id"] == "sess-abc"
    assert session["channel_id"] == ""


def test_store_session_stores_channel_id() -> None:
    store_session("user_chan", {"access_token": "tok", "expires_in": 3600}, channel_id="C999")
    session = get_session("user_chan")
    assert session is not None
    assert session["channel_id"] == "C999"


@patch("requests.post")
def test_create_chat_session_success(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"session_id": "sess-123", "login_url": "https://chat.example.com/login"}
    mock_post.return_value = mock_resp

    session_id, login_url = create_chat_session("https://chat.example.com")
    assert session_id == "sess-123"
    assert login_url == "https://chat.example.com/login"
    mock_post.assert_called_once_with("https://chat.example.com/auth/sessions", timeout=60)


@patch("requests.post")
def test_create_chat_session_raises_on_request_error(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.RequestException("timeout")

    with pytest.raises(AuthenticationError):
        create_chat_session("https://chat.example.com")


@patch("requests.post")
def test_create_chat_session_raises_on_missing_keys(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"unexpected": "response"}
    mock_post.return_value = mock_resp

    with pytest.raises(AuthenticationError):
        create_chat_session("https://chat.example.com")


def test_update_session_channel() -> None:
    store_session("user_upd", {"access_token": "tok", "expires_in": 3600}, chat_session_id="sess-1")
    update_session_channel("user_upd", "C42")
    session = get_session("user_upd")
    assert session is not None
    assert session["channel_id"] == "C42"


def test_update_session_channel_no_op_for_unknown_user() -> None:
    update_session_channel("ghost_user", "C1")  # must not raise


def test_get_session_by_token_found() -> None:
    store_session("user_tok", {"access_token": "my-token", "expires_in": 3600})
    result = get_session_by_token("my-token")
    assert result is not None
    user_id, session = result
    assert user_id == "user_tok"
    assert session["access_token"] == "my-token"


def test_get_session_by_token_not_found() -> None:
    assert get_session_by_token("nonexistent-token") is None


@patch("jira_service.auth.refresh_access_token")
def test_get_valid_token(mock_refresh: MagicMock) -> None:
    store_session("user66", {"access_token": "val1", "refresh_token": "val2", "expires_in": 3600})
    token = get_valid_token("user66")
    assert token == "val1"

    with pytest.raises(AuthenticationError):
        get_valid_token("not_exists")

    store_session("user55", {"access_token": "val1", "refresh_token": "val2", "expires_in": 0})
    mock_refresh.return_value = {"access_token": "new_val", "refresh_token": "val2", "expires_in": 3600}
    token = get_valid_token("user55")
    assert token == "new_val"
