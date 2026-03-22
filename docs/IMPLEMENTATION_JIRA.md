## Overview
This package provides `JiraClient`, a concrete implementation of `IssueTrackerClient`, along with `JiraIssue`, the Jira-specific `Issue` implementation. It handles Jira-specific details such as Atlassian Document Format (ADF) for descriptions, the Transitions API for status changes, and JQL query construction for filtered searches.

## Package Structure
| File | Purpose |
|------|---------|
| `jira_impl.py` | `JiraClient` implementation, `get_client()` factory, and internal helpers |
| `jira_issue.py` | `JiraIssue` implementation, status normalization, and ADF text extraction |
| `__init__.py` | Re-exports `get_client` |

## Authentication
Credentials are read from environment variables:

| Variable | Description |
|----------|-------------|
| `JIRA_BASE_URL` | Base URL of your Jira instance (e.g. `https://myorg.atlassian.net`) |
| `JIRA_USER_EMAIL` | Email address associated with your Atlassian account |
| `JIRA_API_TOKEN` | API token from [Atlassian account settings](https://id.atlassian.com/manage-profile/security/api-tokens) |

## Usage
```python
from jira_client_impl import get_client
from work_mgmt_client_interface.issue import IssueUpdate, Status

# Non-interactive: reads credentials from environment variables
client = get_client()

# Interactive: prompts for any missing credentials at runtime
client = get_client(interactive=True)

# Fetch a single issue
issue = client.get_issue("PROJ-42")

# Search for issues (all filters are optional, combined with AND logic)
for issue in client.get_issues(status=Status.IN_PROGRESS, assignee="dev@example.com"):
    print(issue)

# Create an issue
new_issue = client.create_issue(title="Fix login bug", status=Status.TODO)

# Update an issue (only non-None fields are changed)
updated = client.update_issue("PROJ-42", IssueUpdate(status=Status.COMPLETE))

# Delete an issue
client.delete_issue("PROJ-42")
```

## Jira-Specific Behavior
**Status transitions.** Jira does not allow direct status field edits. Status changes are applied via the Jira Transitions API: the client fetches available transitions for the issue and matches them against a built-in map of common transition names. A `JiraError` is raised if no matching transition is available.

**Descriptions.** Jira Cloud stores and returns descriptions in Atlassian Document Format (ADF). `JiraIssue` transparently extracts plain text from ADF on read, and `JiraClient` converts plain text strings to ADF on write.

**Status normalization.** Jira-native status names (e.g. `"Done"`, `"Resolved"`, `"Closed"`) are normalized to the four standard `Status` enum values defined in the interface (`TODO`, `IN_PROGRESS`, `COMPLETE`, `CANCELLED`).

**Search.** `get_issues()` builds a JQL query from the supplied filters and paginates through results automatically, stopping once `max_results` issues have been yielded.

## Tests
Unit tests are located in `tests/`. To run them:

    python -m pytest components/jira_client_impl/tests/test_core_methods.py -v

## Dependencies
```bash
uv add requests
```

Requires Python 3.11+.
