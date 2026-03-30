"""Service-level exceptions for Jira API service."""


class JiraServiceError(Exception):
    """Base exception for Jira service errors."""

    pass


class IssueNotFoundError(JiraServiceError):
    """Raised when an issue cannot be found."""

    pass


class IssueOperationError(JiraServiceError):
    """Raised when an issue operation (create, update, delete) fails."""

    pass


class ClientInitializationError(JiraServiceError):
    """Raised when Jira client cannot be initialized."""

    pass
