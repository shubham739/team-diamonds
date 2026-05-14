# Integration Summary

This document summarizes all active integrations and external dependencies in the production deployment of the Team Diamonds Jira service.

---

## Production Architecture

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
              └── chat-client-api  →  Team 9 Slack Service
                    │
                    ▼
              DynamoDB (team-diamonds-tokens, us-east-2)
```

---

## External Package Dependencies

### 1. `ospd-issue-tracker-api` — Shared Issue Tracker Interface

| | |
|---|---|
| **Source** | `git+https://github.com/tatyanacthomas/ospd_issue_tracker.git@main` |
| **Imported as** | `api.issue`, `api.board` |
| **Used by** | `jira_client_impl`, `jira_service` |
| **Purpose** | Defines the `IssueTrackerClient` ABC, `Issue` ABC, `Status` enum, and `IssueUpdate` dataclass that all implementations must satisfy. Keeps application code vendor-neutral. |

`jira_client_impl` implements `IssueTrackerClient` against the Jira Cloud REST API v3. `jira_service` depends on the interface only — it never imports concrete Jira classes directly.

---

### 2. `llm-integration-api` — LLM Client

| | |
|---|---|
| **Source** | `git+https://github.com/tatyanacthomas/llm_integration_api.git@main` |
| **Imported as** | `llm_integration_api.open_router_impl.open_router_client.OpenRouterClient` |
| **Used by** | `jira_service` (`ai_client_api.py`) |
| **Purpose** | Provides the OpenRouter HTTP client. `ai_client_api.py` wraps it with Jira-specific tool definitions and a chat loop. |

The AI chat flow:
1. User sends `POST /chat` or `POST /chat-relay` with a natural language message.
2. If the message contains `@jira`, the model is given 5 Jira tool schemas (`list_issues`, `get_issue`, `create_issue`, `update_issue`, `delete_issue`).
3. The model responds with tool calls; `_execute_tool()` dispatches each to `jira-client-impl`.
4. The loop runs up to 3 iterations before returning a final reply.

Default model: `anthropic/claude-sonnet-4-6`

Required env var: `OPENROUTER_API_KEY`

---

### 3. `chat-client-api` (Team 9) — Cross-Vertical Slack Integration

| | |
|---|---|
| **Source** | `git+https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source.git`, subdirectory `components/chat_client_api`, branch `main` |
| **Imported as** | `chat_client_api.client` |
| **Used by** | `jira_service` (`main.py`) |
| **Purpose** | Provides the `get_client()` / `register_client()` DI interface for sending messages to Team 9's Slack service. |

At app startup, `jira_service` registers a `SlackChatClient` factory with Team 9's DI system. The `/chat-relay` endpoint then uses `get_client().send_message(channel_id, text)` to post AI replies to a user's selected Slack channel.

If the package is unavailable, `jira_service` falls back to direct HTTP POST to `CHAT_CLIENT_SERVICE_BASE_URL/messages`.

Required env var: `CHAT_CLIENT_SERVICE_BASE_URL` (Team 9's service base URL)

---

## Infrastructure Integrations

### AWS DynamoDB (`team-diamonds-tokens`, `us-east-2`)

Persists user sessions across Lambda instances. Each session record stores:

| Field | Description |
|---|---|
| `userId` | Cognito sub of the user |
| `integrationType` | `"jira"` or `"slack"` |
| `access_token` | Jira OAuth2 access token |
| `chat_session_id` | Team 9 chat session ID |
| `channel_id` | Selected Slack channel |
| `team9_login_url` | Team 9 Slack auth URL (if re-auth needed) |

### Atlassian OAuth2 (`auth.atlassian.com`)

Full Authorization Code flow. Tokens obtained at `/auth/callback` are stored in DynamoDB and used per-request to construct a `JiraClient` via `get_oauth_client(token)`.

Required env vars: `JIRA_OAUTH_CLIENT_ID`, `JIRA_OAUTH_CLIENT_SECRET`, `JIRA_OAUTH_REDIRECT_URI`, `JIRA_CLOUD_ID`

---

## Internal Component Dependencies

| Component | Depends On | Role |
|---|---|---|
| `jira_service` | `jira_client_impl` | Calls Jira via the impl at request time |
| `jira_service` | `ospd-issue-tracker-api` | Imports `IssueTrackerClient`, `Status` |
| `jira_service` | `llm-integration-api` | AI chat via OpenRouter |
| `jira_service` | `chat-client-api` (Team 9) | Posts replies to Slack |
| `jira_client_impl` | `ospd-issue-tracker-api` | Implements the `IssueTrackerClient` ABC |

---

## Deprecated / Inactive Components

These components exist in the repo but are **not** part of the active deployment:

| Component | Status | Notes |
|---|---|---|
| `jira_service_adapter` | Deprecated | HTTP adapter over `jira_service`; not used in production |
| `jira_service_api_client` | Deprecated | Auto-generated client for `jira_service`; only consumer was `jira_service_adapter` |
| `work_mgmt_client_interface` | Deprecated | Replaced by `ospd-issue-tracker-api` (external package) |
| `jira_chat_bridge` | Deprecated | Earlier polling bridge used during cross-team testing |
| `chat_to_issues_integration` | Deprecated | Earlier generalized chat+issue bridge; replaced by Team 9 DI pattern |

---

## Live Endpoints

| URL | Description |
|---|---|
| `https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/docs` | Interactive API docs (Swagger UI) |
| `https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/health` | Health check |

