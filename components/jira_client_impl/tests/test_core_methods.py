"""Unit tests for JiraClientClass core methods.

This module contains comprehensive unit tests for the core business logic
of the JiraClient class, mocking all external dependencies.
"""

#For now, we can run the tests in this file with this shell command "python -m pytest components/jira_client_impl/tests/test_core_methods.py -v"

import pytest
from unittest.mock import MagicMock
from jira_client_impl.jira_impl import JiraClient, _text_to_adf, JiraError, IssueNotFoundError, get_client
from work_mgmt_client_interface.issue import Status, IssueUpdate
import os
from jira_client_impl.jira_board import JiraBoard

#Fixture for mock tests
@pytest.fixture
def jira_client():
    """Returns a JiraClient with mocked internal API methods."""
    client = JiraClient("https://test.atlassian.net", "test@example.com", "dummy_token")
    
    # Mock the internal _get method to prevent real HTTP calls
    client._get = MagicMock()
    
    # Mock the internal _post method to prevent real HTTP calls
    client._post = MagicMock()
    
    # Mock _build_issue to return a simple string for easy verification
    # (Bypasses the need to create fully populated JiraIssue dataclasses for these tests)
    client._build_issue = MagicMock(side_effect=lambda x: f"MockIssue-{x['key']}")
    
    return client

#Tests for get_issues method
def test_get_issues_builds_correct_jql(jira_client):
    # Setup: Tell our mocked _get method what to return when called
    jira_client._get.return_value = {
        "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
        "total": 2
    }

    # Act: Call the method with a specific status filter
    # We wrap it in list() because get_issues is a generator (yield)
    result = list(jira_client.get_issues(status=Status.IN_PROGRESS))

    # Assert: Did it yield our mock issues?
    assert result == ["MockIssue-TEST-1", "MockIssue-TEST-2"]

def test_get_issues_pagination(jira_client):
    # Setup: Simulate Jira returning data across two pages
    # side_effect allows us to return different data on consecutive calls
    jira_client._get.side_effect = [
        {"issues": [{"key": "TEST-1"}, {"key": "TEST-2"}], "total": 3}, # First API call
        {"issues": [{"key": "TEST-3"}], "total": 3}                     # Second API call
    ]

    # Act: Ask for up to 5 results
    result = list(jira_client.get_issues(max_results=5))

    # Assert: It should have combined all 3 issues from the 2 pages
    assert result == ["MockIssue-TEST-1", "MockIssue-TEST-2", "MockIssue-TEST-3"]


def test_get_issues_when_no_issues_exits(jira_client):
    # Setup: Empty response to see verify correct behavior when no issues exist
    jira_client._get.return_value = {"issues": [], "total": 0}

    result = list(jira_client.get_issues())

    assert result == []

#--------------------------- tests for get_client function --------------------------

def test_get_client_raises_when_env_vars_missing_sa():
    # get_client raises EnvironmentError when required env vars are not set
    
    # Setup: Remove all Jira environment variables
    for var in ["JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN"]:
        os.environ.pop(var, None)
    
    # Assert: Should raise EnvironmentError listing the missing variables
    with pytest.raises(EnvironmentError):
        get_client(interactive=False)


def test_get_client_succeeds_when_env_vars_present_sa():
    #get_client returns a valid JiraClient when all required env vars are set

    # Setup: Set all three required environment variables
    os.environ["JIRA_BASE_URL"] = "https://test.atlassian.net"
    os.environ["JIRA_USER_EMAIL"] = "test@example.com"
    os.environ["JIRA_API_TOKEN"] = "dummy_token"

    # Act: Get the client in non-interactive mode
    client = get_client(interactive=False)

    # Assert: Should return a properly instantiated JiraClient
    assert isinstance(client, JiraClient)

#--------------------------- tests for sanitize_input function --------------------------

def test_sanitize_input_escapes_special_chars_sa():
    # special Jira characters are escaped to prevent JQL injection
    from jira_client_impl.jira_impl import sanitize_input
    
    # Act: Pass a string containing a special character (double quote)
    result = sanitize_input('hello "world"')
    
    # Assert: The double quotes should be escaped with a backslash
    assert '\\"' in result

#--------------------------- tests for _raise_for_status method --------------------------


def test_raise_for_status_ok_response_does_not_raise_sa():
    #successful (2xx) response does not raise any exception

    # Setup: Simulate a 200 OK response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True

    # Assert: No exception should be raised for a successful response
    JiraClient._raise_for_status(mock_response)  


def test_raise_for_status_404_raises_issue_not_found_sa():
    # 404 response raises IssueNotFoundError, not a generic JiraError.

    # Setup: Simulate a 404 response — url is included in the error message
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.url = "https://test.atlassian.net/rest/api/3/issue/BAD-1"
    
    # Assert: Should raise IssueNotFoundError specifically, not a generic JiraError
    with pytest.raises(IssueNotFoundError):
        JiraClient._raise_for_status(mock_response)


def test_raise_for_status_500_raises_jira_error_sa():
    #non-404 error response raises JiraError with the status code in the message
    # Setup: Simulate a 500 server error — json() returns error detail
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.ok = False
    mock_response.json.return_value = {"error": "server error"}
    
    # Assert: Any non-ok, non-404 response should raise a JiraError
    with pytest.raises(JiraError):
        JiraClient._raise_for_status(mock_response)

#-------------------------- tests for update_issue method --------------------------

def test_update_issue_title_sa(jira_client):
    #update_issue correctly sends an updated title field to the Jira API
    
    # Setup: Mock _put for the update call, get_issue returns the refreshed issue
    jira_client._put = MagicMock(return_value={})
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Update just the title — other fields remain None and should not be sent
    update = IssueUpdate(title="New Title")
    result = jira_client.update_issue("TEST-1", update)

    # Assert: _put was called once with the updated fields, and updated issue is returned
    jira_client._put.assert_called_once()
    assert result == "MockIssue-TEST-1"


def test_update_issue_with_status_calls_transition_sa(jira_client):
    #update_issue triggers a status transition when status is in the update.

    # Setup: Mock _put and transition method, get_issue returns the refreshed issue
    jira_client._put = MagicMock(return_value={})
    jira_client._apply_status_transition = MagicMock()
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Update with only a new status — no other fields changed
    update = IssueUpdate(status=Status.COMPLETE)
    jira_client.update_issue("TEST-1", update)

    # Assert: Transition was called with the correct issue ID and target status
    jira_client._apply_status_transition.assert_called_once_with("TEST-1", Status.COMPLETE)



def test_update_issue_with_no_changes_skips_put_sa(jira_client):
    # _put is NOT called when the IssueUpdate has no changed fields.

    # Setup: Mock _put and get_issue
    jira_client._put = MagicMock(return_value={})
    jira_client.get_issue = MagicMock(return_value="MockIssue-TEST-1")

    # Act: Pass an empty update with no fields set
    update = IssueUpdate()
    jira_client.update_issue("TEST-1", update)

    # Assert: _put should never be called when there's nothing to update
    jira_client._put.assert_not_called()

#-------------------- tests for _apply_status_transition method --------------------


def test_status_transition_finds_correct_transition_sa(jira_client):
    # Testing correct transition.
    # Mock transitions endpoint response
    jira_client._get.return_value = {
        "transitions": [
            {"id": "11", "name": "Start Progress"},  # matches IN_PROGRESS
            {"id": "21", "name": "Done"}
        ]
    }
    # transition to IN_PROGRESS
    jira_client._apply_status_transition("TEST-5", Status.IN_PROGRESS)
    
    #Checking that the correct transition ID was posted
    jira_client._post.assert_called_once()
    call_args = jira_client._post.call_args
    transition_id = call_args[0][1]["transition"]["id"]
    
    # Should have posted transition ID 11
    assert transition_id == "11"


def test_status_transition_raises_error_when_no_matching_transition_sa(jira_client):
    # Mock transitions endpoint response with no matching transition for COMPLETE
    jira_client._get.return_value = {
        "transitions": [
            {"id": "11", "name": "Start Progress"},
            {"id": "21", "name": "To Do"}
        ]
    }
    
    # Attempt to transition to COMPLETE 
    with pytest.raises(JiraError) as exc_info:
        jira_client._apply_status_transition("TEST-5", Status.COMPLETE)
    
    # Check that the error message indicates no transition found
    assert "No transition" in str(exc_info.value)

#-------------------- tests for _text_to_adf method --------------------

def test_text_to_adf_sa():
    # testing a simple string that is successfully converted to adf forrmat
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
                        "type":"text"
                    }
                ]
            }
        ]
    }
    # Act: Call the method to convert text to ADF
    result = _text_to_adf(ip_text)

    # Assert: the output ADF should match our expected structure
    assert result == expected_adf

def test_text_to_adf_empty_string_sa():
    # testing an empty string input to see if it returns a valid ADF with empty string text
    expected_adf={
        "type":"doc",
        "version":1,
        "content":[
            {
                "type":"paragraph",
                "content":[
                    {
                        "text":"",
                        "type":"text"
                    }
                ]
            }
        ]
    }
    result = _text_to_adf("")
    assert result == expected_adf

def test_text_to_adf_multiline_string_sa(jira_client):
    # testing a multiline string - _text_to_adf wraps entire text in single paragraph
    ip_text="line 1\nline 2\nline 3"
    expected_adf={
        "type":"doc",
        "version":1,
        "content":[
            {
                "type":"paragraph",
                "content":[
                    {"text":ip_text, "type":"text"}
                ]
            }
        ]
    }
    result = _text_to_adf(ip_text)
    assert result == expected_adf

def test_text_to_adf_non_string_input_sa():
    # testing non-string input to see if it raises the expected error
    with pytest.raises(JiraError) as exc_info:
       result = _text_to_adf(12345)  # passing an integer instead of a string
    
    assert str(exc_info.value) == "Input must be a string"

#----------------------------------------------------------------------
#                       JIRA BOARD TESTS
#----------------------------------------------------------------------

@pytest.fixture
def jira_board():
    """Returns a JiraBoard with a mocked JiraClient."""
    mock_client = MagicMock(spec=JiraClient)
    board = JiraBoard(
        _board_id="1",
        _name="Test Board",
        _client=mock_client
    )
    # Mock _get_board_issues to prevent real HTTP calls
    board._get_board_issues = MagicMock()
    return board


# -------------------- tests for properties --------------------

def test_jira_board_id_property_sa(jira_board):
    #the id property returns the correct board ID.
    # Assert: id should match what was passed into the fixture
    assert jira_board.id == "1"


def test_jira_board_name_property_sa(jira_board):
    #the name property returns the correct board name
    # Assert: name should match what was passed into the fixture
    assert jira_board.name == "Test Board"


def test_jira_board_columns_property_sa(jira_board):
    #the columns property returns the default set of board columns.
    # Act: Get the columns
    columns = jira_board.columns

    # Assert: Should contain all 4 default statuses in the correct order
    statuses = [col.status for col in columns]
    assert Status.TODO in statuses
    assert Status.IN_PROGRESS in statuses
    assert Status.COMPLETE in statuses
    assert Status.CANCELLED in statuses


def test_columns_returns_copy_not_original_sa(jira_board):
    #modifying the returned columns list doesn't affect the board's internal state
    # Act: Get columns and modify the returned list
    columns = jira_board.columns
    columns.clear()

    # Assert: The board's internal columns should be unchanged
    assert len(jira_board.columns) == 4


# -------------------- tests for list_issues --------------------

def test_list_issues_returns_all_issues_sa(jira_board):
    #list_issues returns all issues when no status filter is given
    # Setup: Mock _get_board_issues to return two raw issues
    # Mock _build_issue on the client to return simple mock issue objects
    raw_issues = [{"key": "TEST-1"}, {"key": "TEST-2"}]
    jira_board._get_board_issues.return_value = raw_issues

    mock_issue_1 = MagicMock(status=Status.TODO)
    mock_issue_2 = MagicMock(status=Status.IN_PROGRESS)
    jira_board._client._build_issue.side_effect = [mock_issue_1, mock_issue_2]

    # Act: Call list_issues with no filter
    result = jira_board.list_issues()

    # Assert: Both issues should be returned regardless of status
    assert len(result) == 2
    assert mock_issue_1 in result
    assert mock_issue_2 in result


def test_list_issues_filters_by_status_sa(jira_board):
    #list_issues correctly filters issues by the given status
    # Setup: Two issues with different statuses
    raw_issues = [{"key": "TEST-1"}, {"key": "TEST-2"}]
    jira_board._get_board_issues.return_value = raw_issues

    mock_issue_1 = MagicMock(status=Status.TODO)
    mock_issue_2 = MagicMock(status=Status.IN_PROGRESS)
    jira_board._client._build_issue.side_effect = [mock_issue_1, mock_issue_2]

    # Act: Filter by TODO only
    result = jira_board.list_issues(status=Status.TODO)

    # Assert: Only the TODO issue should be returned
    assert len(result) == 1
    assert mock_issue_1 in result
    assert mock_issue_2 not in result


def test_list_issues_returns_empty_when_no_issues_sa(jira_board):
    # list_issues returns an empty list when the board has no issues.
    # Setup: Mock _get_board_issues to return an empty list
    jira_board._get_board_issues.return_value = []

    # Act: Call list_issues with no filter
    result = jira_board.list_issues()

    # Assert: Should return an empty list, not raise an error
    assert result == []


def test_list_issues_returns_empty_when_no_status_match_sa(jira_board):
    #list_issues returns an empty list when no issues match the given status filter.
    # Setup: Board has only TODO issues, but we filter by COMPLETE
    raw_issues = [{"key": "TEST-1"}]
    jira_board._get_board_issues.return_value = raw_issues

    mock_issue_1 = MagicMock(status=Status.TODO)
    jira_board._client._build_issue.return_value = mock_issue_1

    # Act: Filter by a status that no issue has
    result = jira_board.list_issues(status=Status.COMPLETE)

    # Assert: Should return empty list since nothing matches
    assert result == []


def test_list_issues_calls_get_board_issues_with_correct_fields_sa(jira_board):
    #list_issues calls _get_board_issues with the correct fields parameter.

    # Setup: Return empty list to keep test simple
    jira_board._get_board_issues.return_value = []

    # Act: Call list_issues
    jira_board.list_issues()

    # Assert: _get_board_issues should be called with the expected fields
    jira_board._get_board_issues.assert_called_once_with(
        fields="summary,description,status,assignee,duedate"
    )


# -------------------- tests for get_issue --------------------

def test_get_issue_delegates_to_jira_client_sa(jira_board):
    #get_issue calls JiraClient.get_issue with the correct issue ID.

    # Setup: Mock the client's get_issue to return a mock issue
    mock_issue = MagicMock()
    jira_board._client.get_issue.return_value = mock_issue

    # Act: Call get_issue on the board
    result = jira_board.get_issue("TEST-1")

    # Assert: Should have delegated to the client with the correct ID
    jira_board._client.get_issue.assert_called_once_with("TEST-1")
    assert result == mock_issue


def test_get_issue_raises_when_issue_not_found_sa(jira_board):
    """Test that get_issue propagates IssueNotFoundError from the client
    when the requested issue does not exist."""
    from jira_client_impl.jira_impl import IssueNotFoundError

    # Setup: Mock client to raise IssueNotFoundError
    jira_board._client.get_issue.side_effect = IssueNotFoundError("Issue not found")

    # Assert: The error should bubble up from the board to the caller
    with pytest.raises(IssueNotFoundError):
        jira_board.get_issue("FAKE-999")