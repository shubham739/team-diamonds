# Jira Service API Client (`jira-service-api-client`)

## Overview

`jira-service-api-client` is a type-safe HTTP client for the `jira-service`
FastAPI service introduced in HW2.  It was hand-crafted to match the service's
OpenAPI specification (the spec is stored at `openapi.json` in the repository
root and can be regenerated via `make generate-client`).

It is the network layer consumed by `jira-service-adapter`.

## Design

- Built on `httpx` with a persistent `Client` for connection reuse.
- Every public method returns fully-typed dataclasses (`IssueData`) rather
  than raw dicts.
- `ServiceIssueNotFoundError` is raised on 404; `ServiceClientError` for all
  other non-2xx responses.
- Supports use as a context manager (`with JiraServiceClient(...) as c:`).

## Installation

This package is a workspace member — it is installed automatically when you
run `uv sync` from the repository root.

## Usage

```python
from jira_service_api_client import JiraServiceClient, Status

with JiraServiceClient(
    base_url="https://yx6edoh8l4.execute-api.us-east-2.amazonaws.com/default-deployment/docs",
    access_token="<atlassian-oauth2-token>",
) as client:
    # Check service health (no auth required)
    print(client.health())

    # List issues
    issues = client.list_issues(status=Status.IN_PROGRESS, max_results=10)
    for issue in issues:
        print(issue.id, issue.title)

    # Get a single issue
    issue = client.get_issue("PROJ-42")

    # Create an issue
    new_issue = client.create_issue(
        title="Fix the bug",
        description="Details...",
        status=Status.TODO,
        assignee="dev@example.com",
    )

    # Update an issue
    updated = client.update_issue("PROJ-42", title="Fixed the bug", status=Status.COMPLETE)

    # Delete an issue
    client.delete_issue("PROJ-42")
```

## API Reference

### `JiraServiceClient(base_url, access_token)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_url` | `str` | Base URL of the running service |
| `access_token` | `str` | OAuth2 Bearer token |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `health()` | `dict[str, str]` | `GET /health` — no auth |
| `get_issue(issue_id)` | `IssueData` | `GET /issues/{id}` |
| `list_issues(*, ...)` | `list[IssueData]` | `GET /issues` with optional filters |
| `create_issue(*, ...)` | `IssueData` | `POST /issues` |
| `update_issue(issue_id, *, ...)` | `IssueData` | `PUT /issues/{id}` |
| `delete_issue(issue_id)` | `None` | `DELETE /issues/{id}` |

### `IssueData`

```python
@dataclass
class IssueData:
    id: str
    title: str
    description: str
    status: Status          # todo | in_progress | complete | cancelled
    assignee: str | None
    due_date: str | None    # YYYY-MM-DD or None
```

## Regenerating from OpenAPI Spec

The client was generated from the service's OpenAPI specification.
To regenerate after updating the service:

```bash
make generate-client
```

This starts the service locally, fetches `/openapi.json`, and runs
`openapi-python-client generate`.

## Tests

```bash
pytest components/jira_service_api_client/ -v
```
