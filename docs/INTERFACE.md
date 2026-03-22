## Overview
This package defines the contracts that any issue tracker client must implement. It contains no platform-specific logic — only abstract base classes, shared data models, and a factory stub.

## Package Structure
| File | Purpose |
|------|---------|
| `issue.py` | `Issue` ABC, `IssueUpdate` dataclass, and `Status` enum |
| `client.py` | `IssueTrackerClient` ABC, `IssueNotFoundError`, and `get_client()` factory stub |
| `__init__.py` | Re-exports `IssueTrackerClient` and `get_client` |
| `pyproject.toml` | Package metadata and build configuration |

## Core Concepts

### `Status`
An enum with four normalized statuses used across all implementations: `TODO`, `IN_PROGRESS`, `COMPLETE`, `CANCELLED`. Implementations are responsible for mapping platform-native statuses to these values.

### `Issue`
An abstract base class representing a single issue. Concrete implementations must provide the following read-only properties: `id`, `title`, `description`, `status`, `assignee`, and `due_date`.

### `IssueUpdate`
A dataclass used to express partial updates. All fields default to `None`. Only fields set to a non-`None` value are applied during an update. Use `set_fields()` to retrieve only the changed fields as a dict.

```python
update = IssueUpdate(status=Status.IN_PROGRESS, assignee="dev@example.com")
update.set_fields()  # {"status": Status.IN_PROGRESS, "assignee": "dev@example.com"}
```

### `IssueTrackerClient`
An abstract base class defining the full CRUD interface. Implementations must provide:

- `get_issue(issue_id)` — fetch a single issue by ID
- `get_issues(*, title, description, status, assignee, due_date, max_results)` — filtered search returning an iterator; filters are combined with AND logic
- `create_issue(*, title, description, status, assignee, due_date)` — create and return a new issue
- `update_issue(issue_id, update)` — apply an `IssueUpdate` and return the updated issue
- `delete_issue(issue_id)` — delete an issue by ID

### `get_client()`
A factory function stub that concrete implementations replace. Accepts an `interactive` flag:
- `interactive=False` (default): credentials must come from environment variables
- `interactive=True`: the implementation may prompt the user for missing credentials

## Tests
Unit tests are located in `tests/`. To run them:

    python -m pytest components/work_mgmt_client_interface/tests/ -v

## Installation
```bash
uv sync
```

Requires Python 3.11+.
