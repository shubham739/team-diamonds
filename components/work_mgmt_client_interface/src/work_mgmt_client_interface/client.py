"""Core client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from work_mgmt_client_interface.issue import Issue, IssueUpdate, Status

__all__ = ["IssueTrackerClient", "get_client"]


class IssueTrackerClient(ABC):
    """Tracks issues."""

    # ------------------------------------------------------------------
    # Issue CRUD (create, read, update, delete)
    # ------------------------------------------------------------------
    @abstractmethod
    def get_issue(self, issue_id: str) -> Issue:
        """Get an issue."""
        """Args:
            issue_id: The unique identifier of the issue

        Notes on usage: Any implementations should use build_issue in issue.py to construct the returned Issue objects

        Returns:
            The corresponding Issue instance

        Raises:
            IssueNotFoundError: If no issue with that ID exists

        """
        raise NotImplementedError

    @abstractmethod
    def get_issues(
        self,
        *, # asterisk indicates that all calls to this method must specify the argument name: get_issues(title="Sample Title")
        title: str | None = None,
        description: str | None = None,
        status: Status | None = None,
        assignee: str | None = None,
        due_date: str | None = None,
        max_results: int = 20,
        ) -> Iterator[Issue]:
        """Get issues."""
        """"
        Args:
        assignee:    Restrict results to issues assigned to this user.
            max_results: Maximum number of issues to return. Defaults to 20
        Notes on usage:
            The method functions with AND logic - will return values that meet ALL of the selected criteria
            Implementation handles "before/after due date" logic, and handles fuzzy match on title and description.
            Will not query properties that are not included in method call.
            Additionally, any implementations should use build_issue in issue.py to construct the returned Issue objects

        Yields:
            An iterator of Issue instances matching all supplied filters. Iterator handles pagination
            of API results more seamlessly than returning all results at once.

        """
        raise NotImplementedError

    @abstractmethod
    def create_issue(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        status: Status | None = None,
        assignee: str | None = None,
        due_date: str | None = None,
        ) -> Issue:
        """Create an issue."""
        """Args:
            title:       Short title for the new issue
            description: Optional long-form description
            status:      Predefined statuses
            assignee:    Username or email of the initial assignee
            due_date:    Due date string (e.g. '2025-12-31')

        Notes on usage: Create a new issue and return the resulting Issue instance

        Returns:
            The newly created Issue

        """
        raise NotImplementedError

    @abstractmethod
    def update_issue(self, issue_id: str, update: IssueUpdate) -> Issue:
        """Update an issue."""
        """Args:
            issue_id: The unique identifier of the issue to update
            update:  An IssueUpdate instance carrying the desired changes

        Notes on usage: Applies a set of changes to an existing issue and return the updated Issue.
        Only the fields explicitly set on will be modified, leaving the other properties unchanged

        Returns:
            The updated Issue instance reflecting the applied changes

        Raises:
            IssueNotFoundError: If no issue with that ID exists

        """
        raise NotImplementedError


    @abstractmethod
    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue."""
        """Args:
            issue_id: The unique identifier of the issue.

        Notes on usage:
            Deletes an issue by ID. Consideration will need to be made on implementation for delete,
            as some Issue Trackers do not allow deletion without archiving first, though this does not
            need to be handled here in the interface.

        Raises:
            IssueNotFoundError: If no issue with that ID exists.

        """
        raise NotImplementedError

class IssueNotFoundError(Exception):
    """Base exception raised when an issue cannot be found by the client."""


def get_client(*, interactive: bool = False) -> IssueTrackerClient:
    """Create instance of client."""
    """
    Args:
        interactive: When True, the implementation can pause, prompt the user for input (login credentials),
                     and wait for input
                     When False, the implementation should rely solely on environment variables or pre-configured credentials
                     which is good for a development environment.

    Returns:
        A concrete IssueTrackerClient instance.

    Raises:
        NotImplementedError: Until replaced by a concrete factory.

    """
    raise NotImplementedError
