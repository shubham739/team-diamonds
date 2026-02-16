"""Core client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod

from work_mgmt_client_interface.issue import Issue

__all__ = ["Client", "get_client"]


class Client(ABC):
    """Abstract base class representing an issue tracking client."""

    @abstractmethod
    def get_issue(self, issue_key: str) -> Issue:
        """Return an issue by key."""
        raise NotImplementedError

    @abstractmethod
    def update_issue(self, issue_key: str, title=None):
        """Update an issue."""
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of the Client."""
    raise NotImplementedError
