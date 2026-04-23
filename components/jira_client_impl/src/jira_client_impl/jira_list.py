"""Jira List implementation — maps a board column to the List contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jira_client_impl.jira_board import JiraBoard

if TYPE_CHECKING:
    from jira_client_impl.jira_impl import JiraClient


@dataclass
class JiraList(List):
    """A Jira board column represented as a List.

    In Jira, a board is divided into columns (e.g. "To Do", "In Progress",
    "Done").  Each column corresponds to one Status value.  This class exposes
    a column as a ``List`` so that callers can enumerate or filter issues by
    column without needing to know Jira-specific internals.

    The ``id`` of a JiraList is encoded as ``"{board_id}:{status_value}"``
    (e.g. ``"123:todo"``), which allows ``JiraClient.get_list()`` to
    reconstruct both the board and the status from a single identifier.

    Args:
        _list_id:  Composite identifier ``"{board_id}:{status_value}"``.
        _board_id: The Jira board this column belongs to.
        _name:     Display name of the column (e.g. "To Do").
        _status:   The normalized Status this column represents.
        _client:   The JiraClient used to fetch issues.

    """

    _list_id: str
    _board_id: str
    _name: str
    _status: Status
    _client: JiraClient

    @property
    def id(self) -> str:
        """Return the composite list identifier."""
        return self._list_id

    @property
    def board_id(self) -> str:
        """Return the id of the parent board."""
        return self._board_id

    @property
    def name(self) -> str:
        """Return the display name of the column."""
        return self._name

    def list_issues(self, *, status: Status | None = None) -> list[Issue]:
        """Return issues in this column.

        Args:
            status: Optional override filter.  Defaults to this column's own
                    status so that only issues belonging to this column are
                    returned.

        Returns:
            A list of Issue instances in this column.

        """
        effective_status = status if status is not None else self._status
        board = JiraBoard(_board_id=self._board_id, _name="", _client=self._client)
        return board.list_issues(status=effective_status)
