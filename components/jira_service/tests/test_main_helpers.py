"""Unit tests for main.py helper functions.

Covers _notify_chat_service, _persist_channel_to_dynamodb,
_load_session_from_dynamodb, _bootstrap_session_for_token,
_parse_status_arg, and _execute_tool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Generator
    from contextlib import AbstractContextManager

pytestmark = [pytest.mark.unit, pytest.mark.circleci]


# ---------------------------------------------------------------------------
# _parse_status_arg
# ---------------------------------------------------------------------------


class TestParseStatusArg:
    def test_none_returns_none(self) -> None:
        from jira_service.main import _parse_status_arg

        assert _parse_status_arg(None) is None

    def test_todo_alias(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("todo") == Status.TO_DO

    def test_in_progress_alias(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("inprogress") == Status.IN_PROGRESS

    def test_done_alias(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("done") == Status.COMPLETED

    def test_cancelled_alias(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("cancelled") == Status.COMPLETED

    def test_canceled_alias(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("canceled") == Status.COMPLETED

    def test_status_prefix_stripped(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("status.in_progress") == Status.IN_PROGRESS

    def test_hyphen_normalized(self) -> None:
        from api.issue import Status

        from jira_service.main import _parse_status_arg

        assert _parse_status_arg("in-progress") == Status.IN_PROGRESS


# ---------------------------------------------------------------------------
# _execute_tool
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_issue() -> MagicMock:
    issue = MagicMock()
    issue.id = "TD-1"
    issue.title = "Test issue"
    issue.desc = "Description"
    issue.status = "in_progress"
    issue.members = []
    issue.due_date = None
    return issue


@pytest.fixture
def mock_exec_client(mock_issue: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get_issue.return_value = mock_issue
    client.create_issue.return_value = mock_issue
    client.update_issue.return_value = mock_issue
    client.get_issues.return_value = iter([mock_issue])
    return client


class TestExecuteTool:
    def test_get_issue(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        result = _execute_tool("get_issue", {"issue_id": "TD-1"}, mock_exec_client)
        assert result["id"] == "TD-1"
        mock_exec_client.get_issue.assert_called_once_with("TD-1")

    def test_create_issue(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        result = _execute_tool("create_issue", {"title": "New", "status": "todo"}, mock_exec_client)
        assert result["id"] == "TD-1"
        mock_exec_client.create_issue.assert_called_once()

    def test_update_issue_no_status(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        result = _execute_tool("update_issue", {"issue_id": "TD-1", "title": "Updated"}, mock_exec_client)
        assert result["id"] == "TD-1"
        mock_exec_client.update_issue.assert_called_once()

    def test_update_issue_same_status_skips_transition(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        # mock_issue.status == "in_progress" and we request "in_progress" → no update_issue call
        result = _execute_tool("update_issue", {"issue_id": "TD-1", "status": "in_progress"}, mock_exec_client)
        assert result["id"] == "TD-1"
        mock_exec_client.update_issue.assert_not_called()

    def test_update_issue_different_status_calls_update(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        result = _execute_tool("update_issue", {"issue_id": "TD-1", "status": "done"}, mock_exec_client)
        assert result["id"] == "TD-1"
        mock_exec_client.update_issue.assert_called_once()

    def test_delete_issue(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        result = _execute_tool("delete_issue", {"issue_id": "TD-1"}, mock_exec_client)
        assert result["status"] == "deleted"
        assert result["issue_id"] == "TD-1"
        mock_exec_client.delete_issue.assert_called_once_with("TD-1")

    def test_unknown_tool_raises(self, mock_exec_client: MagicMock) -> None:
        from jira_service.main import _execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            _execute_tool("nonexistent_tool", {}, mock_exec_client)


# ---------------------------------------------------------------------------
# _notify_chat_service
# ---------------------------------------------------------------------------


class TestNotifyChatService:
    def test_returns_true_on_http_success(self) -> None:
        from jira_service.main import _notify_chat_service

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
            with patch("jira_service.main.CHAT_CLIENT_AVAILABLE", new=False):
                with patch("jira_service.main.httpx.Client") as mock_cls:
                    mock_http = MagicMock()
                    mock_http.__enter__ = MagicMock(return_value=mock_http)
                    mock_http.__exit__ = MagicMock(return_value=False)
                    mock_resp = MagicMock()
                    mock_resp.is_success = True
                    mock_http.post.return_value = mock_resp
                    mock_cls.return_value = mock_http
                    result = _notify_chat_service("C123", "hello", "sess-1")

        assert result is True

    def test_returns_false_on_http_non_2xx(self) -> None:
        from jira_service.main import _notify_chat_service

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
            with patch("jira_service.main.CHAT_CLIENT_AVAILABLE", new=False):
                with patch("jira_service.main.httpx.Client") as mock_cls:
                    mock_http = MagicMock()
                    mock_http.__enter__ = MagicMock(return_value=mock_http)
                    mock_http.__exit__ = MagicMock(return_value=False)
                    mock_resp = MagicMock()
                    mock_resp.is_success = False
                    mock_resp.status_code = 502
                    mock_resp.text = '{"detail":"not_in_channel"}'
                    mock_http.post.return_value = mock_resp
                    mock_cls.return_value = mock_http
                    result = _notify_chat_service("C123", "hello", "sess-1")

        assert result is False

    def test_returns_false_when_no_base_url(self) -> None:
        from jira_service.main import _notify_chat_service

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": ""}):
            with patch("jira_service.main.CHAT_CLIENT_AVAILABLE", new=False):
                result = _notify_chat_service("C123", "hello", "sess-1")

        assert result is False

    def test_returns_false_on_exception(self) -> None:
        from jira_service.main import _notify_chat_service

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
            with patch("jira_service.main.CHAT_CLIENT_AVAILABLE", new=False):
                with patch("jira_service.main.httpx.Client", side_effect=Exception("conn refused")):
                    result = _notify_chat_service("C123", "hello", "sess-1")

        assert result is False


# ---------------------------------------------------------------------------
# _persist_channel_to_dynamodb
# ---------------------------------------------------------------------------


class TestPersistChannelToDynamoDB:
    def test_updates_existing_record(self) -> None:
        from jira_service.main import _persist_channel_to_dynamodb

        existing = {"userId": "u1", "integrationType": "jira", "access_token": "tok-pcd", "channel_id": "OLD"}
        with patch("jira_service.main.boto3.resource") as mock_boto:
            mock_table = MagicMock()
            mock_table.scan.return_value = {"Items": [existing]}
            mock_boto.return_value.Table.return_value = mock_table
            _persist_channel_to_dynamodb("tok-pcd", "NEW")

        call_item = mock_table.put_item.call_args[1]["Item"]
        assert call_item["channel_id"] == "NEW"

    def test_no_op_when_record_not_found(self) -> None:
        from jira_service.main import _persist_channel_to_dynamodb

        with patch("jira_service.main.boto3.resource") as mock_boto:
            mock_table = MagicMock()
            mock_table.scan.return_value = {"Items": []}
            mock_boto.return_value.Table.return_value = mock_table
            _persist_channel_to_dynamodb("tok-pcd", "C1")

        mock_table.put_item.assert_not_called()

    def test_swallows_dynamodb_exception(self) -> None:
        from jira_service.main import _persist_channel_to_dynamodb

        with patch("jira_service.main.boto3.resource", side_effect=Exception("DynamoDB down")):
            _persist_channel_to_dynamodb("tok-pcd", "C1")  # must not raise


# ---------------------------------------------------------------------------
# _load_session_from_dynamodb
# ---------------------------------------------------------------------------


class TestLoadSessionFromDynamoDB:
    def test_restores_session_from_record(self) -> None:
        from jira_service.main import _load_session_from_dynamodb

        record = {
            "userId": "u-ddb",
            "integrationType": "jira",
            "access_token": "tok-ddb-load",
            "chat_session_id": "sess-ddb",
            "channel_id": "C-ddb",
            "team9_login_url": "http://login-ddb",
        }
        with patch("jira_service.main.boto3.resource") as mock_boto:
            mock_table = MagicMock()
            mock_table.scan.return_value = {"Items": [record]}
            mock_boto.return_value.Table.return_value = mock_table
            result = _load_session_from_dynamodb("tok-ddb-load")

        assert result is not None
        user_id, session = result
        assert user_id == "u-ddb"
        assert session["chat_session_id"] == "sess-ddb"
        assert session["team9_login_url"] == "http://login-ddb"

    def test_returns_none_when_not_found(self) -> None:
        from jira_service.main import _load_session_from_dynamodb

        with patch("jira_service.main.boto3.resource") as mock_boto:
            mock_table = MagicMock()
            mock_table.scan.return_value = {"Items": []}
            mock_boto.return_value.Table.return_value = mock_table
            result = _load_session_from_dynamodb("unknown-tok")

        assert result is None

    def test_returns_none_on_exception(self) -> None:
        from jira_service.main import _load_session_from_dynamodb

        with patch("jira_service.main.boto3.resource", side_effect=Exception("error")):
            result = _load_session_from_dynamodb("tok")

        assert result is None


# ---------------------------------------------------------------------------
# _bootstrap_session_for_token
# ---------------------------------------------------------------------------


class TestBootstrapSessionForToken:
    def test_creates_session_for_token(self) -> None:
        from jira_service.main import _bootstrap_session_for_token

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
            with patch("jira_service.main.create_chat_session", return_value=("sess-boot", "http://login-boot")):
                result = _bootstrap_session_for_token("bootstrap-unique-tok-xyz")

        assert result is not None
        _, session = result
        assert session["chat_session_id"] == "sess-boot"

    def test_returns_none_when_no_base_url(self) -> None:
        from jira_service.main import _bootstrap_session_for_token

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": ""}):
            result = _bootstrap_session_for_token("my-tok")

        assert result is None

    def test_returns_none_on_auth_error(self) -> None:
        from jira_service.auth import AuthenticationError
        from jira_service.main import _bootstrap_session_for_token

        with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat"}):
            with patch("jira_service.main.create_chat_session", side_effect=AuthenticationError("down")):
                result = _bootstrap_session_for_token("my-tok-err")

        assert result is None


# ---------------------------------------------------------------------------
# chat-relay: post-failure auth link and channel env override
# ---------------------------------------------------------------------------


_FAKE_TOKEN_H = "helper-bearer-token"
_AUTH_HEADER_H = {"Authorization": f"Bearer {_FAKE_TOKEN_H}"}
_RELAY_BODY_H = {"message": "list my tickets"}

_FAKE_SESSION_H = {
    "access_token": _FAKE_TOKEN_H,
    "chat_session_id": "sess-helper",
    "channel_id": "C-helper",
    "team9_login_url": "",
}


@pytest.mark.integration
class TestChatRelayHelpers:
    @pytest.fixture
    def api_client(self) -> Generator[TestClient, None, None]:
        from jira_service.main import app, get_jira_client

        mock_jira = MagicMock()
        mock_jira.get_issues.return_value = iter([])
        app.dependency_overrides[get_jira_client] = lambda: mock_jira
        client = TestClient(app, raise_server_exceptions=False)
        yield client
        app.dependency_overrides.clear()

    def _mock_session(self, session: dict[str, str]) -> AbstractContextManager[MagicMock]:
        return patch("jira_service.main.get_session_by_token", return_value=("helper-user", session))

    def _mock_or(self, reply: str = "Done.") -> MagicMock:
        from jira_service.ai_client_api import get_openrouter_client
        from jira_service.main import app

        mock_or = MagicMock()
        mock_or.complete.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": reply, "tool_calls": None}}],
        }
        app.dependency_overrides[get_openrouter_client] = lambda: mock_or
        return mock_or

    def test_notify_failure_appends_auth_link(self, api_client: MagicMock) -> None:
        from jira_service.ai_client_api import get_openrouter_client
        from jira_service.main import app

        self._mock_or("Here are your tickets.")
        session = {**_FAKE_SESSION_H, "team9_login_url": "http://team9.example.com/login"}
        try:
            with self._mock_session(session):
                with patch("jira_service.main._notify_chat_service", return_value=False):
                    response = api_client.post("/chat-relay", headers=_AUTH_HEADER_H, json=_RELAY_BODY_H)

            assert response.status_code == 200
            body = response.json()
            assert "Authenticate with Team 9 here" in body["reply"]
            assert "http://team9.example.com/login" in body["reply"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_notify_failure_no_auth_link_when_no_login_url(self, api_client: MagicMock) -> None:
        from jira_service.ai_client_api import get_openrouter_client
        from jira_service.main import app

        self._mock_or("Done.")
        session = {**_FAKE_SESSION_H}  # team9_login_url is ""
        try:
            with self._mock_session(session):
                with patch("jira_service.main._notify_chat_service", return_value=False):
                    response = api_client.post("/chat-relay", headers=_AUTH_HEADER_H, json=_RELAY_BODY_H)

            assert response.status_code == 200
            body = response.json()
            assert "Authenticate" not in body["reply"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_env_channel_id_overrides_session(self, api_client: MagicMock) -> None:
        from jira_service.ai_client_api import get_openrouter_client
        from jira_service.main import app

        self._mock_or("Done.")
        session = {**_FAKE_SESSION_H, "channel_id": "SESSION_CHANNEL"}
        try:
            with self._mock_session(session):
                with patch.dict("os.environ", {"TEAM9_CHANNEL_ID": "ENV_CHANNEL"}):
                    with patch("jira_service.main._notify_chat_service", return_value=True) as mock_notify:
                        response = api_client.post("/chat-relay", headers=_AUTH_HEADER_H, json=_RELAY_BODY_H)

            assert response.status_code == 200
            mock_notify.assert_called_once_with("ENV_CHANNEL", "Done.", "sess-helper")
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)

    def test_auto_select_401_returns_auth_link_reply(self, api_client: MagicMock) -> None:
        import httpx as _httpx

        from jira_service.ai_client_api import get_openrouter_client
        from jira_service.main import app

        app.dependency_overrides[get_openrouter_client] = lambda: MagicMock()
        session = {**_FAKE_SESSION_H, "channel_id": "", "team9_login_url": "http://team9.example.com/login"}
        try:
            with self._mock_session(session):
                with patch.dict("os.environ", {"CHAT_CLIENT_SERVICE_BASE_URL": "http://chat", "TEAM9_CHANNEL_ID": ""}):
                    with patch("jira_service.main.httpx.Client") as mock_cls:
                        mock_http = MagicMock()
                        mock_http.__enter__ = MagicMock(return_value=mock_http)
                        mock_http.__exit__ = MagicMock(return_value=False)
                        mock_resp = MagicMock()
                        mock_resp.status_code = 401
                        mock_http.get.side_effect = _httpx.HTTPStatusError(
                            "401", request=MagicMock(), response=mock_resp,
                        )
                        mock_cls.return_value = mock_http
                        response = api_client.post("/chat-relay", headers=_AUTH_HEADER_H, json=_RELAY_BODY_H)

            assert response.status_code == 200
            body = response.json()
            assert "Authenticate with Team 9 here" in body["reply"]
        finally:
            app.dependency_overrides.pop(get_openrouter_client, None)
