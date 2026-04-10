"""List contract - Core list (board column) representation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from work_mgmt_client_interface.issue import Issue, Status


class List(ABC):
    """Abstract base class representing a list (a named column within a board).

    In issue tracker systems a board is divided into lists — named columns such as
    "To Do", "In Progress", and "Done".  Each list groups issues that share a status.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of this list."""
        raise NotImplementedError

    @property
    @abstractmethod
    def board_id(self) -> str:
        """Return the id of the board this list belongs to."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of this list."""
        raise NotImplementedError

    @abstractmethod
    def list_issues(self, *, status: Status | None = None) -> list[Issue]:
        """Return the issues contained in this list.

        Args:
            status: Optional secondary filter.  When provided only issues whose
                    status matches the given value are returned.

        Returns:
            A list of Issue instances belonging to this list.

        """
        raise NotImplementedError
