from unittest.mock import patch, MagicMock
import pytest
from auth import get_user_info, store_session, exchange_code_for_token, refresh_access_token
from auth import user_sessions



@pytest.fixture
def mock_user_data() -> dict:
    """Sample user data from Jira API."""
    return {
        "account_id": "user123",
        "email": "test@example.com",
        "name": "Test User",
    }

@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear user sessions before each test."""
    user_sessions.clear()
    yield
    user_sessions.clear()


@patch("auth.requests.get")
def test_get_user_info_success(mock_get, mock_user_data):
    """Test successful user info retrieval."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_user_data
    mock_get.return_value = mock_response

    result = get_user_info("valid_token")

    assert result == mock_user_data
    mock_get.assert_called_once()

@patch("auth.requests.get")
def test_get_user_info_failure(mock_get):
    """Test failed user info retrieval."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    result = get_user_info("invalid_token")

    assert result is None

def test_store_session():
    """Test that store_session stores data correctly."""
    # SETUP
    token_data = {
        "access_token": "token123",
        "refresh_token": "refresh123",
        "expires_in": 3600,
    }
    
    store_session("user123", token_data)
    
    stored = user_sessions["user123"]
    assert stored["access_token"] == "token123"
    assert stored["refresh_token"] == "refresh123"
    assert "expires_at" in stored

@patch("auth.requests.post")
def test_exchange_code_for_token_success(mock_post):
    """Test successful post of exchange code for token."""
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "access_value", "refresh_token": "refresh_value", "expires_in": 3600}
    mock_post.return_value = mock_response
    
    result = exchange_code_for_token("correct_code")
    
    assert result == {
        "access_token": "access_value",
        "refresh_token": "refresh_value",
        "expires_in": 3600,
    }

    # Validate that requests.post was called with expected endpoint and form data
    mock_post.assert_called_once()
    called_url = mock_post.call_args.args[0]
    called_data = mock_post.call_args.kwargs["data"]
    assert called_url == "https://auth.atlassian.com/oauth/token"
    assert called_data["grant_type"] == "authorization_code"
    assert called_data["code"] == "correct_code"


@patch("auth.requests.post")
def test_exchange_code_for_token_failure(mock_post):
    """Test failed post of exchange code for token."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_post.return_value = mock_response

    result = exchange_code_for_token("incorrect_code")

    assert result is None
    mock_post.assert_called_once()


@patch("auth.requests.post")
def test_refresh_access_token_success(mock_post):
    """Test successful token refresh via post."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_response

    result = refresh_access_token("refresh_token_value")

    assert result == {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
    }
    mock_post.assert_called_once()
    called_url = mock_post.call_args.args[0]
    called_data = mock_post.call_args.kwargs["data"]
    assert called_url == "https://auth.atlassian.com/oauth/token"
    assert called_data["grant_type"] == "refresh_token"
    assert called_data["refresh_token"] == "refresh_token_value"


@patch("auth.requests.post")
def test_refresh_access_token_failure(mock_post):
    """Test refresh_access_token returns None on non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response

    result = refresh_access_token("invalid_refresh")

    assert result is None
    mock_post.assert_called_once()