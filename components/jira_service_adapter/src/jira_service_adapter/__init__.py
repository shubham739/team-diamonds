"""Jira Service Adapter — implements IssueTrackerClient via the remote Jira FastAPI service."""

from jira_service_adapter.adapter import JiraServiceAdapter, get_client
from jira_service_adapter.issue import ServiceIssue

__all__ = ["JiraServiceAdapter", "ServiceIssue", "get_client"]
