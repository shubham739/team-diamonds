"""Unit tests for JiraClientClass core methods.

This module contains comprehensive unit tests for the core business logic
of the JiraClient class, mocking all external dependencies.
"""

#For now, we can run the tests in this file with this shell command "python -m pytest components/jira_client_impl/tests/test_core_methods.py -v"

import pytest
from unittest.mock import MagicMock
from jira_client_impl.jira_impl import JiraClient, _text_to_adf, JiraError
from work_mgmt_client_interface.issue import Status

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
        _text_to_adf(12345)  # passing an integer instead of a string
    
    assert "Input must be a string" in str(exc_info.value)