"""Tests for the auth module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from jira_service.auth import (
    AuthenticationError,
    TokenRefreshError,
    exchange_code_for_token,
    get_authorize_url,
    get_session,
    get_user_info,
    get_valid_token,
    is_token_expired,
    refresh_access_token,
    store_session,
)


def test_get_authorize_url() -> None:
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
