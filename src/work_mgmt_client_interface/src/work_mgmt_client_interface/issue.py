"""Issue contract - Core issue representation."""

from abc import ABC, abstractmethod

__all__ = ["Issue", "get_issue"]


class Issue(ABC):
    """Abstract base class representing a issue."""

    @property
    @abstractmethod
    def key(self) -> str:
        """Return the unique issue key (e.g., PROJ-123)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the issue summary/title."""
        raise NotImplementedError


    @property
    @abstractmethod
    def status(self) -> str:
        """Return the current issue status."""
        raise NotImplementedError


def get_issue(issue_key: str, raw_data: object) -> Issue:
    """
    Return an instance of an Issue.

    Args:
        issue_key (str): Unique issue identifier.
        raw_data (object): Raw data used to construct the issue.

    Returns:
        Issue: An instance conforming to the Issue contract.

    Raises:
        NotImplementedError: Must be implemented by concrete implementation.
    """
    raise NotImplementedError
