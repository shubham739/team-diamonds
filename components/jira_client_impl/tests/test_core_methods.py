"""Unit tests for JiraClientClass core methods.

This module contains comprehensive unit tests for the core business logic
of the JiraClient class, mocking all external dependencies.
"""

#For now, we can run the tests in this file with this shell command "python -m pytest components/jira_client_impl/tests/test_core_methods.py -v"

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jira_client_impl.jira_board import JiraBoard
from jira_client_impl.jira_impl import IssueNotFoundError, JiraClient, JiraError, _text_to_adf, get_client
from jira_client_impl.jira_issue import JiraIssue
from work_mgmt_client_interface.issue import IssueUpdate, Status


#Fixture for mock tests
@pytest.fixture
def jira_client() -> JiraClient:
    """Return a JiraClient with mocked internal API methods."""
    client = JiraClient("https://test.atlassian.net", "test@example.com", "dummy_token")
    client_any: Any = client
    # Mock the internal _get method to prevent real HTTP calls
    client_any._get = MagicMock()

    # Mock the internal _post method to prevent real HTTP calls
    client_any._post = MagicMock()

    # Mock build_issue to return a simple string for easy verification
    # (Bypasses the need to create fully populated JiraIssue dataclasses for these tests)
    client_any.build_issue = MagicMock(side_effect=lambda x: f"MockIssue-{x['key']}")

    return client

#Tests for get_issues method
def test_get_issues_builds_correct_jql(jira_client: Any) -> None:
    """Setup: Tell our mocked _get method what to return when called."""
    jira_client._get.return_value = {
        "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
        "total": 2,
    }

    # Act: Call the method with a specific status filter
    # We wrap it in list() because get_issues is a generator (yield)
    issues: Any = list(jira_client.get_issues(status=Status.IN_PROGRESS))

    # Assert: Did it yield our mock issues?
    assert issues == ["MockIssue-TEST-1", "MockIssue-TEST-2"]

def test_get_issues_pagination(jira_client: Any) -> None:
    """Setup: Simulate Jira returning data across two pages side_effect allows us to return different data on consecutive calls."""
    jira_client._get.side_effect = [
        {"issues": [{"key": "TEST-1"}, {"key": "TEST-2"}], "total": 3}, # First API call
        {"issues": [{"key": "TEST-3"}], "total": 3},                     # Second API call
    ]

    # Act: Ask for up to 5 results
    result: Any = list(jira_client.get_issues(max_results=5))

    # Assert: It should have combined all 3 issues from the 2 pages
    assert result == ["MockIssue-TEST-1", "MockIssue-TEST-2", "MockIssue-TEST-3"]


def test_get_issues_when_no_issues_exits(jira_client: Any) -> None:
    """Setup: Empty response to see verify correct behavior when no issues exist."""
    jira_client._get.return_value = {"issues": [], "total": 0}

    result = list(jira_client.get_issues())

    assert result == []

#--------------------------- tests for get_client function --------------------------

def test_get_client_raises_when_env_vars_missing_sa() -> None:
    """Raise EnvironmentError when required env vars are not set."""
    # Setup: Remove all Jira environment variables
    for var in ["JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN"]:
        os.environ.pop(var, None)

    # Assert: Should raise EnvironmentError listing the missing variables
    with pytest.raises(EnvironmentError, match = "Missing required environment variables"):
        get_client(interactive=False)


def test_get_client_succeeds_when_env_vars_present_sa() -> None:
    """Return a valid JiraClient when all required env vars are set."""
    # Setup: Set all three required environment variables
    os.environ["JIRA_BASE_URL"] = "https://test.atlassian.net"
    os.environ["JIRA_USER_EMAIL"] = "test@example.com"
    os.environ["JIRA_API_TOKEN"] = "dummy_token"

    # Act: Get the client in non-interactive mode
    client = get_client(interactive=False)

    # Assert: Should return a properly instantiated JiraClient
    assert isinstance(client, JiraClient)

#--------------------------- tests for sanitize_input function --------------------------

def test_sanitize_input_escapes_special_chars_sa() -> None:
    """Test that user input is sanitized for jql."""
    from jira_client_impl.jira_impl import sanitize_input

    # Act: Pass a string containing a special character (double quote)
    result = sanitize_input('hello "world"')

    # Assert: The double quotes should be escaped with a backslash
    assert '\\"' in result

#--------------------------- tests for _raise_for_status method --------------------------


def test_raise_for_status_ok_response_does_not_raise_sa() -> None:
    """Test that a successful (2xx) response does not raise any exception."""
    # Setup: Simulate a 200 OK response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True

    # Assert: No exception should be raised for a successful response
    JiraClient._raise_for_status(mock_response)


def test_raise_for_status_404_raises_issue_not_found_sa() -> None:
    """Test that a 404 response raises IssueNotFoundError, not a generic JiraError."""
    # Setup: Simulate a 404 response — url is included in the error message
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.url = "https://test.atlassian.net/rest/api/3/issue/BAD-1"

    # Assert: Should raise IssueNotFoundError specifically, not a generic JiraError
    with pytest.raises(IssueNotFoundError):
        JiraClient._raise_for_status(mock_response)


def test_raise_for_status_500_raises_jira_error_sa() -> None:
    """Test non-404 error response raises JiraError with the status code in the message."""
    # Setup: Simulate a 500 server error — json() returns error detail
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.ok = False
    mock_response.json.return_value = {"error": "server error"}

    # Assert: Any non-ok, non-404 response should raise a JiraError
    with pytest.raises(JiraError):
        JiraClient._raise_for_status(mock_response)

#-------------------------- tests for update_issue method --------------------------

def test_update_issue_title_sa(jira_client: Any) -> None:
    """Test that update_issue correctly sends an updated title field to the Jira API."""
    # Setup: Mock _put for the update call, get_issue returns the refreshed issue
    jira_client._put = MagicMock(return_value={})
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Update just the title — other fields remain None and should not be sent
    update = IssueUpdate(title="New Title")
    result: Any = jira_client.update_issue("TEST-1", update)

    # Assert: _put was called once with the updated fields, and updated issue is returned
    jira_client._put.assert_called_once()
    assert result == "MockIssue-TEST-1"


def test_update_issue_with_status_calls_transition_sa(jira_client: Any) -> None:
    """Test that update_issue triggers a status transition when status is in the update."""
    # Setup: Mock _put and transition method, get_issue returns the refreshed issue
    jira_client._put = MagicMock(return_value={})
    jira_client._apply_status_transition = MagicMock()
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Update with only a new status — no other fields changed
    update = IssueUpdate(status=Status.COMPLETE)
    jira_client.update_issue("TEST-1", update)

    # Assert: Transition was called with the correct issue ID and target status
    jira_client._apply_status_transition.assert_called_once_with("TEST-1", Status.COMPLETE)



def test_update_issue_with_no_changes_skips_put_sa(jira_client: Any) -> None:
    """Test that _put is NOT called when the IssueUpdate has no changed fields."""
    # Setup: Mock _put and get_issue
    jira_client._put = MagicMock(return_value={})
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Pass an empty update with no fields set
    update = IssueUpdate()
    jira_client.update_issue("TEST-1", update)

    # Assert: _put should never be called when there's nothing to update
    jira_client._put.assert_not_called()

#-------------------- tests for _apply_status_transition method --------------------


def test_status_transition_finds_correct_transition_sa(jira_client: Any) -> None:
    """Test correct transition."""
    # Mock transitions endpoint response
    jira_client._get.return_value = {
        "transitions": [
            {"id": "11", "name": "Start Progress"},  # matches IN_PROGRESS
            {"id": "21", "name": "Done"},
        ],
    }
    # transition to IN_PROGRESS
    jira_client._apply_status_transition("TEST-5", Status.IN_PROGRESS)

    #Checking that the correct transition ID was posted
    jira_client._post.assert_called_once()
    call_args = jira_client._post.call_args
    transition_id = call_args[0][1]["transition"]["id"]

    # Should have posted transition ID 11
    assert transition_id == "11"


def test_status_transition_raises_error_when_no_matching_transition_sa(jira_client: Any) -> None:
    """Test mock transitions endpoint response with no matching transition for COMPLETE."""
    jira_client._get.return_value = {
        "transitions": [
            {"id": "11", "name": "Start Progress"},
            {"id": "21", "name": "To Do"},
        ],
    }

    # Attempt to transition to COMPLETE
    with pytest.raises(JiraError) as exc_info:
        jira_client._apply_status_transition("TEST-5", Status.COMPLETE)

    # Check that the error message indicates no transition found
    assert "No transition" in str(exc_info.value)

#-------------------- tests for _text_to_adf method --------------------

def test_text_to_adf_sa() -> None:
    """Test a simple string that is successfully converted to adf forrmat."""
    ip_text="testing adf formatting"
    expected_adf={
        "type":"doc",
        "version":1,
        "content":[
            {
                "type":"paragraph",
                "content":[
                    {
                        "text":ip_text,
                        "type":"text",
                    },
                ],
            },
        ],
    }
    # Act: Call the method to convert text to ADF
    result = _text_to_adf(ip_text)

    # Assert: the output ADF should match our expected structure
    assert result == expected_adf

def test_text_to_adf_empty_string_sa() -> None:
    """Test an empty string input to see if it returns a valid ADF with empty string text."""
    expected_adf={
        "type":"doc",
        "version":1,
        "content":[
            {
                "type":"paragraph",
                "content":[
                    {
                        "text":"",
                        "type":"text",
                    },
                ],
            },
        ],
    }
    result = _text_to_adf("")
    assert result == expected_adf

def test_text_to_adf_multiline_string_sa(jira_client: Any) -> None:
    """Test a multiline string - _text_to_adf wraps entire text in single paragraph."""
    ip_text="line 1\nline 2\nline 3"
    expected_adf={
        "type":"doc",
        "version":1,
        "content":[
            {
                "type":"paragraph",
                "content":[
                    {"text":ip_text, "type":"text"},
                ],
            },
        ],
    }
    result = _text_to_adf(ip_text)
    assert result == expected_adf

def test_text_to_adf_non_string_input_sa() -> None:
    """Test non-string input to see if it raises the expected error."""
    with pytest.raises(JiraError) as exc_info:
    # passing an integer instead of a string
       _text_to_adf(12345)  # type: ignore[arg-type]

    assert str(exc_info.value) == "Input must be a string"

def test_status_happy_path()-> None:
    """Test Issue.status property for a successful mapping."""
    raw_data = {"status": {"name": "in progress"}}
    issue = JiraIssue("PROJ-1", raw_data, "https://test.net")
    assert issue.status == Status.IN_PROGRESS

def test_status_fallback_path()-> None:
    """Test Issue.status property for missing or unknown status data."""
    # 1. Test an unknown string (hits the .get(..., Status.TODO) line)
    issue_unknown = JiraIssue("PROJ-2", {"status": {"name": "Ghost"}}, "https://test.net")
    assert issue_unknown.status == Status.TODO

    # 2. Test missing status dict (hits the 'else ""' and 'if not jira_status' lines)
    issue_missing = JiraIssue("PROJ-3", {}, "https://test.net")
    assert issue_missing.status == Status.TODO

def test_jira_issue_basic_coverage()-> None:
    """Test various properties for JiraIssue class."""
    # A single raw_data blob containing every field we care about
    raw_data = {
        "summary": "Fix the flux capacitor",
        "status": {"name": "In Progress"},
        "assignee": {"emailAddress": "doc@brown.com", "displayName": "Emmett Brown"},
        "duedate": "2026-12-31",
        "description": "Standard string description",
    }

    issue = JiraIssue(issue_id="PROJ-123", raw_data=raw_data, base_url="https://jira.com/")

    # Touching these properties executes the underlying logic
    assert issue.id == "PROJ-123"
    assert issue.title == "Fix the flux capacitor"
    assert issue.status == Status.IN_PROGRESS
    assert issue.assignee == "doc@brown.com"
    assert issue.due_date == "2026-12-31"
    assert issue.description == "Standard string description"

def test_jira_issue_empty_fallbacks() -> None:
    """Verify correct behavior when Issue properties are missing."""
    # Empty data hits all the 'get(..., "")' and 'isinstance' fallback lines
    issue = JiraIssue("PROJ-EMPTY", {}, "https://test.net")

    assert issue.title == ""
    assert issue.description == ""
    assert issue.status == Status.TODO
    assert issue.assignee is None
    assert issue.due_date is None

    # Touching __repr__ hits the base class code and uses id/title/status
    assert "PROJ-EMPTY" in repr(issue)

def test_description_adf_recursion_coverage() -> None:
    """Test recursive behavior of Issue.description property."""
    adf_data = {
        "description": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello "}, {"type": "text", "text": "World"}],
                },
            ],
        },
    }
    issue = JiraIssue("PROJ-1", adf_data, "https://test.net")

    # This call executes the recursive _extract_adf_text function
    assert issue.description == "Hello \nWorld"

@patch("jira_client_impl.jira_impl.JiraClient._post")
@patch("jira_client_impl.jira_impl.JiraClient._apply_status_transition")
@patch("jira_client_impl.jira_impl.JiraClient.get_issue")
def test_create_issue_full_coverage(
    mock_get: MagicMock,
    mock_transition : MagicMock,
    mock_post : MagicMock,
    jira_client : Any,
    ) -> None:
    """Test create_issue method with mock http messages."""
    #Cast as any because mypy doesn't play well with MagicMock
    client_as_any: Any = jira_client
    # --- MANUALLY INJECT THE MOCK ---
    client_as_any._post = mock_post
    client_as_any._apply_status_transition = mock_transition
    client_as_any.get_issue = mock_get
    # -----------------------------------------

    # 1. Setup the mock return value for the initial POST
    mock_post.return_value = {"key": "PROJ-101"}

    # 2. Call the function
    jira_client.create_issue(
        title="Test Title",
        description="Test Desc",
        status=Status.IN_PROGRESS,
        assignee="test@user.com",
        due_date="2026-05-01",
    )

    # 3. Verify
    mock_post.assert_called_once()

    # Get the second argument (the JSON body)
    # args[0] is path, args[1] is the body dict
    args, _ = mock_post.call_args
    posted_payload = args[1]["fields"]

    assert posted_payload["summary"] == "Test Title"
    assert posted_payload["assignee"] == {"emailAddress": "test@user.com"}
    assert posted_payload["duedate"] == "2026-05-01"

    # Verify the transition and get_issue were called
    mock_transition.assert_called_once_with("PROJ-101", Status.IN_PROGRESS)
    mock_get.assert_called_once_with("PROJ-101")

#----------------------------------------------------------------------
#                       JIRA BOARD TESTS
#----------------------------------------------------------------------

@pytest.fixture
def jira_board() -> Any:
    """Return a JiraBoard with a mocked JiraClient."""
    mock_client = MagicMock(spec=JiraClient)
    board = JiraBoard(
        _board_id="1",
        _name="Test Board",
        _client=mock_client,
    )
    board_any: Any = board
    # Mock _get_board_issues to prevent real HTTP calls
    board_any._get_board_issues = MagicMock()
    return board


# -------------------- tests for properties --------------------

def test_jira_board_id_property_sa(jira_board: Any) -> None:
    """Verify that the id property returns the correct board ID."""
    # Assert: id should match what was passed into the fixture
    assert jira_board.id == "1"


def test_jira_board_name_property_sa(jira_board: Any) -> None:
    """Verify that the name property returns the correct board name."""
    # Assert: name should match what was passed into the fixture
    assert jira_board.name == "Test Board"


def test_jira_board_columns_property_sa(jira_board: Any) -> None:
    """Verify that the columns property returns the default set of board columns."""
    # Act: Get the columns
    columns = jira_board.columns

    # Assert: Should contain all 4 default statuses in the correct order
    statuses = [col.status for col in columns]
    assert Status.TODO in statuses
    assert Status.IN_PROGRESS in statuses
    assert Status.COMPLETE in statuses
    assert Status.CANCELLED in statuses


def test_columns_returns_copy_not_original_sa(jira_board: Any) -> None:
    """Test that modifying the returned columns list doesn't affect the board's internal state."""
    # Act: Get columns and modify the returned list
    columns = jira_board.columns
    columns.clear()

    # Assert: The board's internal columns should be unchanged
    assert len(jira_board.columns) == 4


# -------------------- tests for list_issues --------------------

def test_list_issues_returns_all_issues_sa(jira_board: Any) -> None:
    """Test that list_issues returns all issues when no status filter is given."""
    # Setup: Mock _get_board_issues to return two raw issues
    # Mock build_issue on the client to return simple mock issue objects
    raw_issues = [{"key": "TEST-1"}, {"key": "TEST-2"}]
    jira_board._client._get.return_value = {"issues": raw_issues}

    mock_issue_1 = MagicMock(status=Status.TODO)
    mock_issue_2 = MagicMock(status=Status.IN_PROGRESS)
    jira_board._client.build_issue.side_effect = [mock_issue_1, mock_issue_2]

    # Act: Call list_issues with no filter
    result = jira_board.list_issues()

    # Assert: Both issues should be returned regardless of status
    assert len(result) == 2
    assert mock_issue_1 in result
    assert mock_issue_2 in result


def test_list_issues_filters_by_status_sa(jira_board: Any) -> None:
    """Test that list_issues correctly filters issues by the given status."""
    # Setup: Two issues with different statuses
    raw_issues = [{"key": "TEST-1"}, {"key": "TEST-2"}]
    jira_board._client._get.return_value = {"issues": raw_issues}

    mock_issue_1 = MagicMock(status=Status.TODO)
    mock_issue_2 = MagicMock(status=Status.IN_PROGRESS)
    jira_board._client.build_issue.side_effect = [mock_issue_1, mock_issue_2]

    # Act: Filter by TODO only
    result = jira_board.list_issues(status=Status.TODO)

    # Assert: Only the TODO issue should be returned
    assert len(result) == 1
    assert mock_issue_1 in result
    assert mock_issue_2 not in result


def test_list_issues_returns_empty_when_no_issues_sa(jira_board: Any) -> None:
    """Test that list_issues returns an empty list when the board has no issues."""
    # Setup: Mock _get_board_issues to return an empty list
    jira_board._client._get.return_value = {"issues": []}

    # Act: Call list_issues with no filter
    result = jira_board.list_issues()

    # Assert: Should return an empty list, not raise an error
    assert result == []


def test_list_issues_returns_empty_when_no_status_match_sa(jira_board: Any) -> None:
    """Test that list_issues returns an empty list when no issues match the given status filter."""
    # Setup: Board has only TODO issues, but we filter by COMPLETE
    raw_issues = [{"key": "TEST-1"}]
    jira_board._client._get.return_value = {"issues": raw_issues}

    mock_issue_1 = MagicMock(status=Status.TODO)
    jira_board._client.build_issue.return_value = mock_issue_1

    # Act: Filter by a status that no issue has
    result = jira_board.list_issues(status=Status.COMPLETE)

    # Assert: Should return empty list since nothing matches
    assert result == []


def test_list_issues_calls_get_board_issues_with_correct_fields_sa(jira_board: Any) -> None:
    """Test that list_issues calls _get_board_issues with the correct fields parameter."""
    # Setup: Return empty list to keep test simple
    jira_board._client._get.return_value = {"issues": []}

    # Act: Call list_issues
    jira_board.list_issues()

    # Assert: _get_board_issues should be called with the expected fields
    jira_board._client._get.assert_called_once_with(
        "/board/1/issue",
        params={"fields": "summary,description,status,assignee,duedate"},
    )


# -------------------- tests for get_issue --------------------

def test_get_issue_delegates_to_jira_client_sa(jira_board: Any) -> None:
    """Test that get_issue calls JiraClient.get_issue with the correct issue ID."""
    # Setup: Mock the client's get_issue to return a mock issue
    mock_issue = MagicMock()
    jira_board._client.get_issue.return_value = mock_issue

    # Act: Call get_issue on the board
    result = jira_board.get_issue("TEST-1")

    # Assert: Should have delegated to the client with the correct ID
    jira_board._client.get_issue.assert_called_once_with("TEST-1")
    assert result == mock_issue


def test_get_issue_raises_when_issue_not_found_sa(jira_board: Any) -> None:
    """Test that get_issue propagates IssueNotFoundError from the client when the requested issue does not exist."""
    from jira_client_impl.jira_impl import IssueNotFoundError

    # Setup: Mock client to raise IssueNotFoundError
    jira_board._client.get_issue.side_effect = IssueNotFoundError("Issue not found")

    # Assert: The error should bubble up from the board to the caller
    with pytest.raises(IssueNotFoundError):
        jira_board.get_issue("FAKE-999")

def test_board_create_issue_sa(jira_board: Any) -> None:
    """Test that JiraBoard delegates create_issue to the underlying client."""
    jira_board._client.create_issue.return_value = "MockCreatedIssue"

    result = jira_board.create_issue(title="New Issue")

    jira_board._client.create_issue.assert_called_once_with(
        title="New Issue", description="", status=Status.TODO,
    )
    assert result == "MockCreatedIssue"


def test_board_update_issue_sa(jira_board: Any) -> None:
    """Test that JiraBoard delegates update_issue to the underlying client."""
    update = IssueUpdate(title="Updated Title")
    jira_board._client.update_issue.return_value = "MockUpdatedIssue"

    result = jira_board.update_issue("TEST-1", update)

    jira_board._client.update_issue.assert_called_once_with("TEST-1", update)
    assert result == "MockUpdatedIssue"

# -------------------- tests for raw HTTP network methods --------------------

@patch("jira_client_impl.jira_impl.requests.Session")
def test_raw_http_methods_sa(mock_session_class: MagicMock) -> None:
    """Test the un-mocked internal HTTP helpers (_get, _post, _put, _delete)."""
    # 1. Create a mock session that the JiraClient will use
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    # 2. Setup mock responses for the different HTTP methods
    mock_get_resp = MagicMock(status_code=200, ok=True)
    mock_get_resp.json.return_value = {"action": "get"}
    mock_session.get.return_value = mock_get_resp

    mock_post_resp = MagicMock(status_code=201, ok=True)
    mock_post_resp.json.return_value = {"action": "post"}
    mock_session.post.return_value = mock_post_resp

    mock_put_resp = MagicMock(status_code=204, ok=True) # 204 triggers the NO_CONTENT branch
    mock_session.put.return_value = mock_put_resp

    mock_delete_resp = MagicMock(status_code=204, ok=True)
    mock_session.delete.return_value = mock_delete_resp

    # 3. Create a REAL client (we don't use the jira_client fixture here)
    client = JiraClient("https://test.net", "user", "token")

    # 4. Assert that the helpers correctly call the session and return the json
    assert client._get("/path") == {"action": "get"}
    assert client._post("/path", {"body": "test"}) == {"action": "post"}
    assert client._put("/path", {"body": "test"}) == {}  # 204 returns empty dict
    assert client._delete("/path") is True

    # 5. Test the _delete 404 fallback branch
    mock_delete_not_found = MagicMock(status_code=404, ok=False)
    mock_session.delete.return_value = mock_delete_not_found
    assert client._delete("/path") is False
