"""Issue contract - Core issue representation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields as dataclass_fields
from enum import Enum

#we can alter these, these are just 4 common statuses that I thought would be good starting point. 
class Status(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"

@dataclass
#opted for dataclass instead of standard class so that partial updates can be made
#dataclass handles __init__, __repr__, and __eq__
class IssueUpdate:
    """
    All fields default to None. During an update, only fields explicitly changed to non-None value will be changed.
    """

    title: str | None = None
    description: str | None = None
    status: Status | None = None
    assignee: str | None = None    
    due_date: str | None = None
    
    def set_fields(self) -> dict:
        """Return a dict containing only the fields explicitly set to non-None values (the only ones to be updated)
            """
        return {f.name: getattr(self, f.name) for f in dataclass_fields(self) if getattr(self, f.name) is not None}

class Issue(ABC):
    """Abstract base class representing a issue."""
    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the issue"""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the title of the issue."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the description of the issue."""
        raise NotImplementedError

    @property
    @abstractmethod
    def status(self) -> Status:
        """Return the status of the issue."""
        raise NotImplementedError

    @property
    @abstractmethod
    def assignee(self) -> str | None:
        """Return the username or email of the assignee, or None if unassigned."""
        raise NotImplementedError

    @property
    @abstractmethod
    def due_date(self) -> str | None:
        """Return the due date, or None if not set."""
        raise NotImplementedError

    #equivalent to Javas .toString()
    def __repr__(self) -> str:
        return f"<Issue id={self.id!r} title={self.title!r} status={self.status}>"

def build_issue(issue_id: str, raw_data: dict) -> "Issue":
    """
    Purpose: Retrieves API data and builds an Issue, returning an Issue instance
    
    Notes on usage:
        Responses from API's will arrive as a blob of JSON. Rather than unpacking every field at the call site before passing it in, we hand the whole blob to get_issue() and let the implementation determine how to pick out the fields it needs.
    
    Args:
        issue_id: The unique identifier for the issue.
        raw_data: The raw data dict from the upstream API used to construct the issue.

    Returns:
        Issue: An instance conforming to the Issue contract.

    Raises:
        NotImplementedError: Must be implemented by concrete implementation.
    """
    raise NotImplementedError
