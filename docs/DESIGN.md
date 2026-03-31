# Design

## Purpose

This project provides a unified Python interface for interacting with issue tracking systems. The goal is to allow application code to work with issues from any platform (Jira, Linear, GitHub Issues, etc.) through a single, consistent API — without being coupled to any one vendor's SDK or data format.

In HW2 the local library is complemented by a deployable FastAPI microservice. Consumers can swap between the local implementation and the remote service transparently — the contract never changes.

---

## Architecture Overview

```
work-mgmt-client-interface/       # Abstract contracts only (IssueTrackerClient ABC)
jira-client-impl/                 # Jira-specific local library (calls Jira REST API directly)
jira-service/                     # FastAPI service (wraps jira-client-impl over HTTP)
jira-service-api-client/          # Type-safe HTTP client for the FastAPI service
jira-service-adapter/             # Adapter: implements IssueTrackerClient via the service client
```

### Option 1 — Local Library

```
main.py
  └─ JiraClient (jira-client-impl)
       └─ Jira REST API
```

### Option 2 — Remote Service

```
main.py
  └─ JiraServiceAdapter (jira-service-adapter)
       └─ JiraServiceClient (jira-service-api-client)  [HTTP]
            └─ jira-service (FastAPI)
                 └─ JiraClient (jira-client-impl)
                      └─ Jira REST API
```

The consumer (`main.py`) calls `get_client()` from either `jira_client_impl` or `jira_service_adapter`. Because both implement `IssueTrackerClient`, the rest of the code is identical.

---

## Request Flow (Remote path)

1. Consumer calls `adapter.get_issues(title="bug")`.
2. `JiraServiceAdapter` translates the call to `JiraServiceClient.list_issues(title="bug")`.
3. `JiraServiceClient` sends `GET /issues?title=bug` with a Bearer token to the deployed service.
4. The FastAPI service validates the token, delegates to `JiraClient.get_issues(title="bug")`.
5. `JiraClient` builds a JQL query and calls the Jira REST API.
6. Results travel back up: `JiraIssue` → JSON response → `IssueData` → `ServiceIssue` (implements `Issue`).

---

## API Design

### Authentication — OAuth 2.0 Authorization Code Flow

The service implements the standard web-server OAuth 2.0 flow:

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/login` | GET | Redirect browser to Jira's authorization URL |
| `/auth/callback` | GET | Receive code, exchange for tokens, store session |
| `/auth/logout` | GET | Invalidate session |

Tokens are stored server-side in an in-memory session dict (keyed by `account_id`). The client receives a bearer token it passes on subsequent requests via `Authorization: Bearer <token>`.

### Issue Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | No | Liveness check |
| `/issues` | GET | Yes | List issues with optional filters |
| `/issues` | POST | Yes | Create a new issue |
| `/issues/{id}` | GET | Yes | Fetch a single issue |
| `/issues/{id}` | PUT | Yes | Update an issue |
| `/issues/{id}` | DELETE | Yes | Delete an issue |

### Error Handling

- `404` → `IssueNotFoundError` in the adapter layer; surfaced as `ServiceIssueNotFoundError` in the HTTP client.
- `422` → Invalid query parameters or issue data.
- `503` → Jira client not configured (missing env vars).
- `500` → Unexpected errors (logged server-side).

---

## Adapter Pattern Rationale

The Adapter pattern solves the location-transparency problem: consumers should not care whether the Jira client runs in the same process or on a remote server.

**Without the adapter:**
```python
# Consumer must know which concrete class to use
from jira_client_impl import get_client          # local only
from jira_service_adapter import get_client      # remote only
```

**With the adapter (both options behind the same interface):**
```python
from work_mgmt_client_interface.client import IssueTrackerClient

def do_work(client: IssueTrackerClient) -> None:
    for issue in client.get_issues(status=Status.TODO):
        print(issue.title)

# Inject either — no change to do_work
do_work(jira_client_impl.get_client())       # local
do_work(jira_service_adapter.get_client())   # remote
```

`JiraServiceAdapter` is the glue: it implements `IssueTrackerClient` and delegates each method to `JiraServiceClient`, translating domain types (`Status`) to their service equivalents and mapping `ServiceIssueNotFoundError` back to `IssueNotFoundError`.

---

## Testing Strategy

| Layer | Test type | What is tested |
|---|---|---|
| `work_mgmt_client_interface` | Unit | Interface contracts, `IssueUpdate.set_fields()` |
| `jira_client_impl` | Unit | JQL builder, status mapping, ADF conversion; mocked HTTP |
| `jira_service` | Unit + Integration | FastAPI endpoints with `TestClient`; OAuth flow mocked |
| `jira_service_api_client` | Unit | `IssueData.from_dict`, error mapping |
| `jira_service_adapter` | Unit | Adapter delegation, error translation, `get_client` factory |
| Root `tests/e2e/` | E2E | Full stack against live Jira; skipped when credentials absent |

CI runs all tests except `local_credentials`-marked ones. Integration tests against the live Jira API run only on `main` using the `jira-client` context.

---

## Key Design Decisions

### Partial updates via `IssueUpdate`
Updates are expressed as a dataclass where every field defaults to `None`. Only fields explicitly set to a non-`None` value are sent to the API, avoiding accidental overwrites.

### Iterator return for `get_issues()`
Returns `Iterator[Issue]` rather than a list to support lazy pagination — the caller never manages pagination logic.

### Session tokens over a database
The OAuth tokens are stored in an in-memory dict keyed by `account_id`. A full database would introduce a new deployable component; session storage achieves the same security goal for this scope.

### `openapi-python-client` replaced by hand-written client
The auto-generated client from `openapi-python-client` used `attrs` and had no `py.typed` marker, making mypy integration awkward. The hand-written `JiraServiceClient` is a thin, fully-typed wrapper that mirrors the OpenAPI spec exactly and is easier to maintain.

---

## Deployment

The service is deployed to **Render** as a Docker container.

- **URL**: configured via `JIRA_OAUTH_REDIRECT_URI` environment variable
- **Health check**: `GET /health` → `{"status": "ok"}`
- **OpenAPI spec**: `GET /openapi.json`
- **Environment variables** (set via Render's secrets manager — never committed):
  - `JIRA_OAUTH_CLIENT_ID`
  - `JIRA_OAUTH_CLIENT_SECRET`
  - `JIRA_OAUTH_REDIRECT_URI`
  - `JIRA_BASE_URL`
  - `JIRA_USER_EMAIL`
  - `JIRA_API_TOKEN`

CircleCI triggers a Render deploy hook on every push to `hw2` after tests pass (via the `render-deploy` context).

---

## Adding a New Implementation

To add support for a new issue tracker:

1. Create a new package (e.g. `linear-client-impl`).
2. Implement `Issue` (subclass the ABC, provide all properties).
3. Implement `IssueTrackerClient` (subclass the ABC, implement all methods).
4. Implement `get_client()`, returning your concrete client.
5. Map the platform's native statuses to the four `Status` enum values.
6. Export `get_client` from `__init__.py`.

The interface layer requires no changes.

---

## Known Limitations

- `create_issue()` does not accept a `project`/`board` parameter (required by most trackers).
- `Status` covers four common states; richer workflows must map to the nearest equivalent.
- In-memory session storage is not suitable for multi-instance deployments.
- The interface currently models issues only (no comments, attachments, or sprints).
