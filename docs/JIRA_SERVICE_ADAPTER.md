# Jira Service Adapter (`jira-service-adapter`)

## Overview

`jira-service-adapter` is the **Adapter Pattern** component introduced in HW2.
It implements the `IssueTrackerClient` abstract interface from
`work-mgmt-client-interface` by delegating every call through
`JiraServiceClient` to the deployed `jira-service` over HTTP.

This achieves **location transparency**: consumer code that works with
`jira-client-impl.get_client()` (local library) works identically with
`jira-service-adapter.get_client()` (remote service) — no changes required.

## Architecture

```
Consumer (e.g. main.py)
  │  calls IssueTrackerClient methods
  ▼
JiraServiceAdapter          ← this package
  │  delegates via HTTP client
  ▼
JiraServiceClient           ← jira-service-api-client
  │  HTTP Bearer token
  ▼
jira-service (FastAPI)      ← deployed service
  │
  ▼
Jira REST API
```

## Usage

```python
# Remote path (production)
from jira_service_adapter import get_client

client = get_client()          # reads JIRA_SERVICE_BASE_URL + JIRA_SERVICE_ACCESS_TOKEN
issues = list(client.get_issues(status="in_progress"))

# Sanity check: interchangeable with the local library
from jira_client_impl import get_client as get_local_client

local_client  = get_local_client()   # IssueTrackerClient via Jira API directly
remote_client = get_client()         # IssueTrackerClient via HTTP service

# Both produce identical results — same interface contract
```

## `get_client()` Factory

```python
def get_client(*, interactive: bool = False) -> JiraServiceAdapter
```

Reads two environment variables:

| Variable | Description |
|----------|-------------|
| `JIRA_SERVICE_BASE_URL` | Base URL of the deployed service (e.g. `https://team-diamonds.onrender.com`) |
| `JIRA_SERVICE_ACCESS_TOKEN` | Atlassian OAuth2 access token for the Bearer header |

Raises `OSError` if either variable is missing.

## Error Translation

The adapter translates service-layer exceptions into the interface-layer
exceptions that consumers expect:

| Source exception | Translated to |
|-----------------|---------------|
| `ServiceIssueNotFoundError` | `IssueNotFoundError` (from `work-mgmt-client-interface`) |
| `ServiceClientError` | Re-raised as-is |

## Tests

```bash
pytest components/jira_service_adapter/ -v
```

Tests use `unittest.mock.MagicMock` for `JiraServiceClient` — no network
required.
