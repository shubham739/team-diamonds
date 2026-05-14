# Design

## Purpose

This project provides a unified Python interface for interacting with issue tracking systems. The goal is to allow application code to work with issues from any platform (Jira, Linear, GitHub Issues, etc.) through a single, consistent API — without being coupled to any one vendor's SDK or data format.

The service is deployed as a FastAPI application on AWS Lambda behind API Gateway. It exposes a REST API for Jira issue management, an AI-powered chat interface backed by an LLM, and cross-vertical integration with Team 9's Slack service.

---

## Architecture Overview

```
ospd-issue-tracker-api (external)  # Abstract contracts: IssueTrackerClient ABC, Issue ABC, Status enum
jira-client-impl/                  # Jira-specific implementation (calls Jira REST API v3 directly)
jira-service/                      # FastAPI service deployed on AWS Lambda via Mangum
```

### Production Deployment

```
Browser / Frontend (CloudFront)
  │
  ▼  HTTPS
API Gateway  →  AWS Lambda (Mangum)
                    │
                    ▼
              jira-service  (FastAPI)
              ├── jira-client-impl  →  Jira REST API v3
              ├── llm-integration-api  →  OpenRouter LLM
              └── chat-client-api (Team 9)  →  Slack
                    │
                    ▼
              DynamoDB (team-diamonds-tokens, us-east-2)
```

Application code imports from `ospd-issue-tracker-api` (the shared interface). `jira_service` never imports concrete Jira classes directly — it receives an `IssueTrackerClient` instance from `get_jira_client()` at request time.

### Deprecated Components (not in production)

The following components were designed as an alternative remote-service access path but are not used in the current deployment:

- **`jira-service-api-client`** — auto-generated HTTP client for `jira-service`
- **`jira-service-adapter`** — adapter that implements the `ospd-issue-tracker-api` contract via the service client
- **`work_mgmt_client_interface`** — local package replaced by the external `ospd-issue-tracker-api`
- **`jira_chat_bridge`** — earlier cross-team polling bridge
- **`chat_to_issues_integration`** — earlier generalized chat+issue bridge

---

## Request Flow

### Issue CRUD

1. Client sends `GET /issues?title=bug` with a Bearer token.
2. `get_jira_client()` constructs a per-user `JiraClient` from the OAuth2 token (or falls back to Basic Auth).
3. `JiraClient.get_issues(title="bug")` builds a JQL query and calls the Jira REST API.
4. Results are serialized to JSON and returned.

### AI Chat (`/chat` and `/chat-relay`)

1. Client sends `POST /chat` with `{"message": "@jira list open bugs"}`.
2. `jira_mode_requested()` detects the `@jira` trigger; Jira tool schemas are passed to the LLM.
3. OpenRouter returns tool calls; `_execute_tool()` dispatches each to the live `JiraClient`.
4. The loop runs up to 3 iterations before returning the final reply.
5. For `/chat-relay`, the reply is also posted to the user's selected Slack channel via Team 9's `chat-client-api`.

---

## API Design

### Authentication — OAuth 2.0 Authorization Code Flow
The service supports two authentication strategies, chosen based on environment configuration:

#### OAuth2 Bearer Token Path (Production, Multi-User)
When `JIRA_CLOUD_ID` is set, the service uses Atlassian OAuth2 bearer tokens for Jira API access.

The standard web-server OAuth 2.0 flow is implemented:

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/login` | GET | Redirect browser to Jira's authorization URL |
| `/auth/callback` | GET | Receive code, exchange for tokens, store session |
| `/auth/logout` | GET | Invalidate session |

Tokens are stored server-side in an in-memory session dict (keyed by `account_id`) for refresh purposes. The client receives a bearer token it passes on subsequent requests via `Authorization: Bearer <token>`.

#### Basic Auth Fallback Path (Development, Single-User)
When `JIRA_CLOUD_ID` is not set, the service falls back to Basic Auth using `JIRA_USER_EMAIL` and `JIRA_API_TOKEN`. This is the single-developer path and is also used when the Bearer token in the request header is a service-level API token.

In both paths, the FastAPI dependency `get_jira_client` selects the appropriate JiraClient instance based on available environment variables.

#### Session Persistence (DynamoDB)
Because the service runs on AWS Lambda (stateless, multiple instances), sessions are persisted to the `team-diamonds-tokens` DynamoDB table (`us-east-2`). This ensures that the OAuth callback and subsequent requests can hit different Lambda instances without losing session state. Each record stores: `userId`, `access_token`, `chat_session_id`, `channel_id`, and `team9_login_url`.

### Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | No | Liveness check |
| `/auth/login` | GET/POST | No | Initiate Jira or Slack OAuth flow |
| `/auth/callback` | GET | No | OAuth2 callback — exchange code, create Team 9 session, store in DynamoDB |
| `/auth/logout` | GET | No | Clear session |
| `/auth/channels` | GET | Yes | List Team 9 Slack channels for the authenticated user |
| `/auth/select-channel` | POST | Yes | Store the user's chosen Slack channel |
| `/issues` | GET | Yes | List issues (with optional filters) |
| `/issues` | POST | Yes | Create a new issue |
| `/issues/{id}` | GET | Yes | Fetch a single issue |
| `/issues/{id}` | PUT | Yes | Update an issue |
| `/issues/{id}` | DELETE | Yes | Delete an issue |
| `/chat` | POST | Yes | AI natural-language Jira assistant |
| `/chat-relay` | POST | Yes | AI chat + post reply to Slack via Team 9 |

### Error Handling

- `404` → `IssueNotFoundError` in the adapter layer; surfaced as `ServiceIssueNotFoundError` in the HTTP client.
- `422` → Invalid query parameters or issue data.
- `503` → Jira client not configured (missing env vars).
- `500` → Unexpected errors (logged server-side).

---

## Cross-Vertical Integration (Team 9)

The `/chat-relay` endpoint extends the AI chat flow with cross-vertical posting to Team 9's Slack service. This uses Team 9's published `chat-client-api` package via their `get_client()` / `register_client()` DI pattern.

At startup, `jira_service` registers a `SlackChatClient` factory with Team 9's DI system. `_notify_chat_service()` calls `get_client().send_message(channel_id, text)` and falls back to a direct HTTP POST if the package is unavailable.

Users must complete a two-part auth flow (Jira OAuth2 + Slack connect) before using `/chat-relay`. Both sessions are stored in DynamoDB.

See [CROSS_VERTICAL_INTEGRATION.md](CROSS_VERTICAL_INTEGRATION.md) for full details.

---

## Testing Strategy

| Layer | Test type | What is tested |
|---|---|---|
| `jira_client_impl` | Unit | JQL builder, status mapping, ADF conversion; mocked HTTP |
| `jira_service` | Unit + Integration | FastAPI endpoints with `TestClient`; OAuth flow mocked; AI chat loop; cross-vertical relay |
| Root `tests/e2e/` | E2E | Full stack against live Jira; skipped when credentials absent |
| Root `tests/integration/` | Integration | Cross-vertical integration with Team 9's `chat-client-api` |

CI runs two workflows depending on the branch:

`build_and_test` — runs on all branches except main. Executes build → lint → unit_test → circleci_test → report_summary. No integration tests or deployment.

`main` — runs on main. Executes the same stages plus integration_test (against the live Jira API, using the jira-client context) and deploy (to AWS Lambda, using the aws-deploy context). The report_summary job aggregates results from all three test stages before deployment proceeds. 

Integration tests run with -m "integration and not local_credentials", so tests requiring local credentials are always skipped in CI.

---

## Key Design Decisions

### Partial updates via keyword fields
Updates are expressed as optional keyword fields (`title`, `desc`, `members`, `due_date`, `status`, `board_id`). Only fields explicitly provided are sent to the API, avoiding accidental overwrites.

### Iterator return for `get_issues()`
The interface returns `Iterator[Issue]` so callers can consume results as a stream without needing list semantics.

The local `jira_client_impl` pages Jira lazily, fetching results in batches from the Jira REST API. The remote path preserves the iterator contract at the adapter layer, but the service API currently returns a single issue list per request rather than a fully streamed, multi-request pagination flow.

### Session storage in DynamoDB
OAuth tokens and Team 9 session IDs are persisted to DynamoDB (`team-diamonds-tokens`, `us-east-2`) rather than only in-memory. This is required because the service runs on AWS Lambda where multiple instances may handle different requests for the same user. An in-memory fallback is retained for local development.

---

## Deployment

The service is deployed to AWS Lambda via Mangum, behind API Gateway. `render.yaml` exists for Render.com deployment but is not used by the current CI pipeline.

- **Live API docs**: `https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/docs`
- **Health check**: `GET /health` → `{"status": "ok"}`
- **Environment Variables** (set via deployment secrets manager — never committed):

| Variable | Purpose |
|---|---|
| `JIRA_OAUTH_CLIENT_ID` | Atlassian OAuth2 app client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | Atlassian OAuth2 app client secret |
| `JIRA_OAUTH_REDIRECT_URI` | OAuth callback URL |
| `JIRA_CLOUD_ID` | Atlassian cloud instance ID (enables OAuth2 path) |
| `JIRA_BASE_URL` | Jira instance URL (Basic Auth fallback) |
| `JIRA_USER_EMAIL` | User email (Basic Auth fallback) |
| `JIRA_API_TOKEN` | API token (Basic Auth fallback) |
| `OPENROUTER_API_KEY` | OpenRouter key for AI chat |
| `CHAT_CLIENT_SERVICE_BASE_URL` | Team 9's Slack service base URL |
| `FRONTEND_URL` | CloudFront frontend URL (CORS + redirect target) |
| `TEAM9_CHANNEL_ID` | Optional: hardcode a Slack channel ID |

CircleCI triggers an AWS Lambda deployment after tests pass (via the `aws-deploy` context).

---

## Adding a New Implementation

To add support for a new issue tracker:

1. Create a new package (e.g. `trello-client-impl`).
2. Implement `Issue` (subclass the ABC, provide all properties).
3. Implement the `api` client contract (subclass the ABC, implement all methods).
4. Implement `get_client()`, returning your concrete client.
5. Map the platform's native statuses to the four `Status` enum values.
6. Export `get_client` from `__init__.py`.

The interface layer requires no changes.

---

## Known Limitations

- `create_issue()` does not accept a `project`/`board` parameter (required by most trackers).
- `Status` covers four common states; richer workflows must map to the nearest equivalent.
- The interface currently models issues only (no comments, attachments, or sprints).
- `/chat-relay` requires the user to complete a two-part auth flow (Jira + Slack) before use; incomplete auth returns a re-authentication prompt rather than an error.
