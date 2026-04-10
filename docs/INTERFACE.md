## Overview
This package defines the contracts that any issue tracker client must implement. It contains no platform-specific logic — only abstract base classes, shared data models, and a factory stub.

## Package Structure
| File | Purpose |
|------|---------|
| `issue.py` | `Issue` ABC and `Status` enum |
| `board.py` | Board ABC for board/project management |
| `client.py` | Client ABC, `IssueNotFoundError`, and `get_client()` factory stub |
| `__init__.py` | Re-exports the client contract and `get_client` |
| `pyproject.toml` | Package metadata and build configuration |

## Core Concepts

### `Status`
An enum used across implementations with normalized values such as `TO_DO`, `IN_PROGRESS`, and `COMPLETED`. Implementations are responsible for mapping platform-native statuses to these values.

### `Issue`
An abstract base class representing a single issue. Concrete implementations must provide the following read-only properties: `id`, `title`, `description`, `status`, `assignee`, and `due_date`.

### Client Contract
The external `api` package defines the full CRUD interface. Implementations must provide:

- `get_issue(issue_id)` — fetch a single issue by ID
- `get_issues(*, title, desc, status, members, due_date, max_results)` — filtered search returning an iterator; filters are combined with AND logic
- `create_issue(*, title, desc, status, members, due_date, board_id)` — create and return a new issue
- `update_issue(issue_id, *, title, desc, members, due_date, status, board_id)` — apply a partial update and return the updated issue
- `delete_issue(issue_id)` — delete an issue by ID

### `get_client()`
A factory function stub that concrete implementations replace. Accepts an `interactive` flag:
- `interactive=False` (default): credentials must come from environment variables
- `interactive=True`: the implementation may prompt the user for missing credentials

## Installation
```bash
uv sync
```

Requires Python 3.11+.
