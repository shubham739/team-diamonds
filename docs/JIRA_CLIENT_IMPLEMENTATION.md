# Jira Client Implementation

The `jira_client_impl` component is the concrete Jira integration for this project. It implements the abstract interfaces defined in [`ospd-issue-tracker-api`](https://github.com/tatyanacthomas/ospd_issue_tracker) (imported as `api.issue`, `api.board`, etc.), translating generic issue and board operations into Jira Cloud REST API v3 calls.

## What It Does

- **CRUD for issues** — create, read, update, and delete Jira issues
- **Board support** — fetch boards and filter issues by status
- **Status normalization** — maps Jira-native statuses (e.g. `"Done"`, `"Resolved"`) to the canonical `Status` enum (`TO_DO`, `IN_PROGRESS`, `COMPLETED`)
- **Status transitions** — Jira requires going through a Transitions API to change status; this is handled automatically
- **ADF handling** — Jira Cloud uses Atlassian Document Format for descriptions; the client converts to/from plain text transparently
- **JQL injection protection** — all user-supplied strings are sanitized before being injected into JQL queries

## Modules

| File | Purpose |
|---|---|
| `jira_impl.py` | `JiraClient` — main client class, HTTP helpers, JQL builder, factory functions |
| `jira_issue.py` | `JiraIssue` — issue implementation, ADF parsing, status normalization |
| `jira_board.py` | `JiraBoard` — board implementation, delegates issue operations to `JiraClient` |

## Authentication

Two modes are supported:

**API Token (Basic Auth)** — for scripts and CI:
```bash
JIRA_BASE_URL=https://myorg.atlassian.net
JIRA_USER_EMAIL=me@example.com
JIRA_API_TOKEN=<token>
```
```python
from jira_client_impl.jira_impl import get_client
client = get_client()
```

**OAuth2 Bearer Token** — for the web app flow (token comes from the OAuth2 callback):
```bash
JIRA_CLOUD_ID=<cloud-id>
```
```python
from jira_client_impl.jira_impl import get_oauth_client
client = get_oauth_client(access_token="<atlassian_oauth2_token>")
```

## Quick Example

```python
client = get_client()

# List open issues
for issue in client.get_issues(status=Status.TO_DO):
    print(issue.id, issue.title)

# Create an issue
new_issue = client.create_issue(board_id="PROJ", title="Fix login bug", description="Steps to reproduce...")

# Update status
client.update_issue(new_issue.id, status=Status.IN_PROGRESS)

# Delete
client.delete_issue(new_issue.id)
```

## Running Tests

```bash
# Unit tests only (no credentials needed)
uv run pytest components/jira_client_impl/ -m unit

# With coverage (must meet 85% threshold)
uv run pytest components/jira_client_impl/ --cov=components/jira_client_impl/src
```
