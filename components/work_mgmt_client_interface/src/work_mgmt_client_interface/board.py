"""Core board contract definitions and factory placeholder."""


from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from work_mgmt_client_interface.issue import Issue, IssueUpdate, Status


@dataclass(frozen=True)
class BoardColumn:
    """Abstract base class for board column."""

    status: Status
    name: str

class Board(ABC):
    """Abstract base class for a board."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return board id."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Return name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def columns(self) -> list[BoardColumn]:
        """Board columns for showing the different statuses."""
        raise NotImplementedError
        # ---- Issue access ----
    @abstractmethod
    def list_issues(self, *, status: Status | None = None) -> list[Issue]:
        """Return issues on this board.

        If status is provided, return only issues in that column.
        Returned list order should be stable for UI rendering.
        """
        raise NotImplementedError

    @abstractmethod
    def get_issue(self, issue_id: str) -> Issue:
        """Return a single issue by id, or raise if not found."""
        raise NotImplementedError

    # ---- Mutations ----
    @abstractmethod
    def create_issue(
        self,
        *,
        title: str,
        description: str = "",
        status: Status = Status.TODO,
    ) -> Issue:
        """Create a new issue on the board and return it."""
        raise NotImplementedError

    @abstractmethod
    def update_issue(self, issue_id: str, update: IssueUpdate) -> Issue:
        """Update part of an issue.

        Only fields explicitly set in IssueUpdate should be changed.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue from the board."""
        raise NotImplementedError

def build_board(board_id: str, raw_data: dict) -> Board:
    """Build and returns a board object."""
    raise NotImplementedError
