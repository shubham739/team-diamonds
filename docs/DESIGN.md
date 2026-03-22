# Design

## Purpose
This project provides a unified Python interface for interacting with issue tracking systems. The goal is to allow application code to work with issues from any platform (Jira, Linear, GitHub Issues, etc.) through a single, consistent API — without being coupled to any one vendor's SDK or data format.

## Architecture
The project is split into two layers:

**Interface layer** (`work-mgmt-client-interface`) defines the contracts: what an issue looks like, what operations a client must support, and what data goes in and out. It contains no platform-specific logic.

**Implementation layer** (e.g. `jira-client-impl`) fulfills those contracts for a specific platform. Each implementation is a separate package that depends on the interface package.

```
work-mgmt-client-interface/       # Abstract contracts only
    issue.py                      # Issue, IssueUpdate, Status
    client.py                     # IssueTrackerClient, get_client()

jira-client-impl/                 # Jira-specific implementation
    jira_issue.py                 # JiraIssue, status normalization, ADF parsing
    jira_impl.py                  # JiraClient, get_client()
```

Application code imports from the interface layer and calls `get_client()` from whichever implementation is configured. Swapping platforms means swapping the implementation package — the rest of the application is unchanged.

## Key Design Decisions

### Partial updates via `IssueUpdate`
Updates are expressed as an `IssueUpdate` dataclass where every field defaults to `None`. Only fields explicitly set to a non-`None` value are sent to the API. This avoids accidental overwrites and makes it easy to express targeted changes without fetching the full issue first.

### `build_issue()` as a construction convention
The interface defines a `build_issue(issue_id, raw_data)` function signature that implementations follow to construct `Issue` instances from raw API responses. This keeps the messy JSON-unpacking logic inside the implementation 

### Iterator return for `get_issues()`
`get_issues()` returns an `Iterator[Issue]` rather than a list. This allows implementations to paginate through large result sets lazily, only fetching the next page when needed, without the caller needing to manage pagination logic.

### `get_client()` factory with `interactive` flag
The factory function accepts an `interactive` flag to support two usage contexts. In non-interactive mode, credentials must be present in environment variables — suitable for scripts and automated environments. In interactive mode, the implementation may prompt for missing values — suitable for local development and CLI tools.

## Adding a New Implementation
To add support for a new issue tracker:

1. Create a new package (e.g. `linear-client-impl`).
2. Implement `Issue` (subclass the ABC, provide all properties).
3. Implement `IssueTrackerClient` (subclass the ABC, implement all methods).
4. Implement `get_client()`, returning your concrete client.
5. Map the platform's native statuses to the four `Status` enum values.
6. Export `get_client` from `__init__.py`.

The interface layer requires no changes.

## Error Handling
`IssueNotFoundError` is defined in the interface layer so callers can catch it without importing from a specific implementation. Implementations subclass it and raise it consistently whenever an issue ID cannot be found. Platform-specific errors (e.g. `JiraError`) are separate and not part of the shared contract.

## Known Limitations
- `create_issue()` does not yet accept a `project` / `board parameter`. This is a required field in most issue trackers and will need to be added to the interface.
- The `Status` enum covers four common statuses. Platforms with richer workflow states will need to map those states to the nearest equivalent
- The interface currently models issues only. Comments, attachments, sprints, and other platform concepts are out of scope.
