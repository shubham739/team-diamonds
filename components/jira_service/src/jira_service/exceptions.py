"""Service-level exceptions for Jira API service."""


class JiraServiceError(Exception):
    """Base exception for Jira service errors."""


class IssueNotFoundError(JiraServiceError):
    """Raised when an issue cannot be found."""


class IssueOperationError(JiraServiceError):
    """Raised when an issue operation (create, update, delete) fails."""


class ClientInitializationError(JiraServiceError):
    """Raised when Jira client cannot be initialized."""
