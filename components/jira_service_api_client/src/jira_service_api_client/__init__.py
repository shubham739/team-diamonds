"""Jira Service API client — type-safe HTTP client for the Jira FastAPI service."""

from jira_service_api_client.client import JiraServiceClient, ServiceClientError, ServiceIssueNotFoundError
from jira_service_api_client.models import IssueData, Status

__all__ = [
    "IssueData",
    "JiraServiceClient",
    "ServiceClientError",
    "ServiceIssueNotFoundError",
    "Status",
]
