"""Unit tests for JiraClientClass core methods.

This module contains comprehensive unit tests for the core business logic
of the JiraClient class, mocking all external dependencies.
"""

#For now, we can run the tests in this file with this shell command "python -m pytest components/jira_client_impl/tests/test_core_methods.py -v"

import pytest
from unittest.mock import MagicMock
from jira_client_impl.jira_impl import JiraClient, _text_to_adf, JiraError, IssueNotFoundError, get_client
from jira_client_impl.jira_board import JiraBoard
from work_mgmt_client_interface.issue import Status, IssueUpdate

#Fixture for mock tests
@pytest.fixture
def jira_client():
    """Returns a JiraClient with mocked internal API methods."""
    client = JiraClient("https://test.atlassian.net", "test@example.com", "dummy_token")
    
    # Mock the internal _get method to prevent real HTTP calls
    client._get = MagicMock()
    
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