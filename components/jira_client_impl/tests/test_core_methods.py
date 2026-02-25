"""Unit tests for JiraClientClass core methods.

This module contains comprehensive unit tests for the core business logic
of the JiraClient class, mocking all external dependencies.
"""

#For now, we can run the tests in this file with this shell command "python -m pytest components/jira_client_impl/tests/test_core_methods.py -v"

import pytest
from unittest.mock import MagicMock
from jira_client_impl.jira_impl import JiraClient
from work_mgmt_client_interface.issue import Status

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