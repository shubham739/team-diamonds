# Jira Service (`jira-service`)

> **Interactive API Docs (live):** https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/docs

## Overview

`jira-service` is the FastAPI deployment unit that wraps `jira-client-impl` over HTTP, exposes an OpenAPI spec, and implements the full OAuth 2.0 Authorization Code flow so the service can act on behalf of individual Atlassian users. It also exposes an AI-powered `/chat` endpoint backed by an LLM (via OpenRouter) that can read and write Jira issues on the user's behalf using natural language.

The service is deployed to AWS Lambda (via Mangum) behind API Gateway, with sessions persisted in DynamoDB so multiple Lambda instances share state.

## Architecture

```
Browser / Frontend
  │
  ▼  HTTP (Bearer token)
jira-service  (FastAPI + Mangum → AWS Lambda)
  │                │
  ▼                ▼
jira-client-impl   ai_client_api (OpenRouter LLM)
  │                     │
  ▼                     ▼ tool calls
Jira REST API v3   Jira client methods (list/create/update/delete issues)
```

## Modules

| File | Purpose |
|---|---|
| `main.py` | FastAPI app — all routes, auth flow, DynamoDB session persistence, CORS |
| `ai_client_api.py` | LLM integration adapter — OpenRouter client, Jira tool definitions, chat loop |
| `auth.py` | OAuth2 helpers — token exchange, session store, Atlassian API calls |
| `handler.py` | AWS Lambda entrypoint via Mangum |
| `exceptions.py` | Custom service-level exceptions |

---

## AI Chat (`ai_client_api.py`)

This module is the LLM integration layer for the service. It brings in an external dependency — [`llm-integration-api`](https://github.com/tatyanacthomas/llm_integration_api) (installed from git) — and wraps it with Jira-specific tool definitions and a chat loop.

### External dependency

```
llm-integration-api  (git: tatyanacthomas/llm_integration_api, branch: main)
  └── llm_integration_api.open_router_impl.open_router_client.OpenRouterClient
  └── llm_integration_api.interface.exceptions.LLMIntegrationError
```

`ai_client_api.py` imports `OpenRouterClient` from this package as the underlying HTTP client for calling [OpenRouter](https://openrouter.ai), then wraps it in a local `OpenRouterClient` adapter that adds:
- Tool-call support (`tools` + `tool_choice: auto` in the payload)
- A consistent `OpenRouterError` exception type
- Attribution headers (`HTTP-Referer`, `X-Title`)

The default model is `anthropic/claude-sonnet-4-6`, configurable at construction time.

### What it provides to the rest of the app

`main.py` imports the following from `ai_client_api`:

| Export | Purpose |
|---|---|
| `OpenRouterClient` | LLM client used by the `/chat` endpoint |
| `OpenRouterError` | Exception type caught and translated to HTTP 503 |
| `get_openrouter_client` | Factory function — reads `OPENROUTER_API_KEY` from env |
| `JIRA_TOOLS` | Tool schema list passed to the model so it can call Jira operations |
| `GENERAL_CHAT_SYSTEM_PROMPT` | System prompt controlling model behavior and `@jira` gating |
| `jira_mode_requested(msg)` | Returns `True` if the user message contains `@jira` |
| `normalize_chat_message(msg)` | Strips the `@jira` trigger token before sending to the model |

### How the chat loop works

1. The `/chat` endpoint receives a `{"message": "..."}` body.
2. If the message contains `@jira`, Jira tools are enabled and passed to the model.
3. The model responds with either a plain text answer or a tool call.
4. If a tool call is returned, `_execute_tool()` in `main.py` dispatches it to the live `JiraClient` and appends the result back to the message history.
5. The loop runs up to 3 iterations (allowing multi-step tool chains) before returning the final reply.

### Jira tools available to the model

| Tool | What it does |
|---|---|
| `list_issues` | Search issues with optional filters (status, title, members, due date) |
| `get_issue` | Fetch a single issue by key (e.g. `PROJ-42`) |
| `create_issue` | Create a new issue |
| `update_issue` | Update fields on an existing issue (partial update) |
| `delete_issue` | Permanently delete an issue |

### Required environment variable

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | API key for OpenRouter — required for `/chat` to work |

---

## Authentication

The service supports two authentication strategies, chosen based on environment configuration:

#### OAuth2 Bearer Token Path (Production, Multi-User)
When `JIRA_CLOUD_ID` is set, the service uses Atlassian OAuth2 bearer tokens for Jira API access. Each request carries a per-user access token obtained via the OAuth2 Authorization Code flow. Sessions are stored in-memory and persisted to DynamoDB so they survive Lambda cold starts and cross-instance redirects.

#### Basic Auth Fallback Path (Development, Single-User)
When `JIRA_CLOUD_ID` is not set, the service falls back to Basic Auth using `JIRA_USER_EMAIL` and `JIRA_API_TOKEN`. The FastAPI dependency `get_jira_client` selects the appropriate client automatically.

---

## Cross-Vertical Slack Integration (Team 9 DI)

`jira-service` integrates with Team 9's Slack chat service via a dependency injection pattern. The service never directly instantiates a Slack client at the call site — instead it registers a factory with Team 9's DI registry at startup, and retrieves the client through that registry when needed.

### Components involved

Only one file from `chat_to_issues_integration` is used:
- `slack_client.py` — provides `SlackChatClient`, which wraps `slack_sdk.WebClient`

The rest of `chat_to_issues_integration` (`app.py`, `chat_client.py`, `mock_chat_client.py`) is **not** used by `jira_service`.

### How the DI wiring works

**Step 1 — Import Team 9's registry functions (not Slack)**

```python
# main.py — guarded by try/except ImportError
from chat_client_api.client import get_client as get_chat_client
from chat_client_api.client import register_client as register_chat_client
```


**Step 2 — Register a `SlackChatClient` factory at startup (inside `lifespan`)**

```python
# main.py — lifespan() runs once on server startup
from chat_to_issues_integration.slack_client import SlackChatClient

def create_slack_client() -> SlackChatClient:
    return SlackChatClient()  # reads SLACK_BOT_TOKEN from env

register_chat_client(create_slack_client)  # stores the factory, not the instance
```

The factory function is passed to Team 9's registry — no `SlackChatClient` instance is created at this point. The import of `SlackChatClient` is deferred inside the `lifespan` function body and is itself wrapped in `try/except Exception`, so the server starts normally even if `SLACK_BOT_TOKEN` is missing or `chat_to_issues_integration` is unavailable.

**Step 3 — Retrieve and use via the registry (`_notify_chat_service`)**

```python
# main.py — _notify_chat_service()
if CHAT_CLIENT_AVAILABLE and get_chat_client is not None:
    chat_client = get_chat_client()           # asks Team 9's registry what was registered
    chat_client.send_message(channel_id, text)  # calls the Slack method indirectly
```

`_notify_chat_service` has no import of `SlackChatClient`, `slack_client.py`, or `slack_sdk`. It calls `get_chat_client()` and invokes only the abstract `send_message` interface. If the registry call fails, the function falls back to a direct HTTP POST to `CHAT_CLIENT_SERVICE_BASE_URL`.

### Summary of what is and isn't direct

| Concern | How it's handled |
|---|---|
| Slack client instantiation | Deferred — only happens when Team 9's registry calls the factory |
| Slack method calls (`send_message`) | Indirect — called through `get_chat_client()` return value |
| `slack_sdk` import | Only in `slack_client.py` — never imported in `main.py` |
| Failure handling | Both the registration (step 2) and the call (step 3) are wrapped in `try/except` |

### Required environment variable

| Variable | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token (`xoxb-...`) — required for `SlackChatClient.__init__` |

---

## Endpoints

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | No | Returns `{"status": "ok"}` |
| `GET` | `/auth/login` | No | Redirect browser to Atlassian OAuth2 consent |
| `POST` | `/auth/login` | No | Return auth URL for frontend-initiated flows (Jira or Slack) |
| `GET` | `/auth/callback` | No | OAuth2 callback — exchange code, store session, redirect to frontend |
| `GET` | `/auth/channels` | Yes | List Team 9 chat channels linked to the user's session |
| `POST` | `/auth/select-channel` | Yes | Store the user's chosen chat channel |
| `GET` | `/auth/logout` | No | Clear user session |
| `GET` | `/` | Yes | Fetch 5 most-recent issues |
| `GET` | `/issues` | Yes | List issues with optional filters |
| `GET` | `/issues/{issue_id}` | Yes | Fetch a single issue |
| `POST` | `/issues` | Yes | Create a new issue |
| `PUT` | `/issues/{issue_id}` | Yes | Update an issue (partial) |
| `DELETE` | `/issues/{issue_id}` | Yes | Delete an issue |
| `POST` | `/chat` | Yes | AI-powered chat with optional `@jira` Jira tool access |
| `POST` | `/chat-relay` | Yes | Relay endpoint for cross-team chat integration |

## Request / Response

`POST /issues` and `PUT /issues/{issue_id}` accept a JSON body:

```json
{
  "title": "string",
  "desc": "string",
  "status": "to_do | in_progress | completed",
  "members": ["user@example.com"],
  "due_date": "YYYY-MM-DD"
}
```

All fields are optional for `PUT` (partial update semantics).

`POST /chat` accepts:
```json
{ "message": "Show me open issues" }
```
Prefix with `@jira` to enable Jira tool calls:
```json
{ "message": "@jira create a task called Fix login bug" }
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_OAUTH_CLIENT_ID` | Yes | Atlassian OAuth2 app client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | Yes | Atlassian OAuth2 app client secret |
| `JIRA_OAUTH_REDIRECT_URI` | Yes | Must match the callback URL registered in Atlassian |
| `OPENROUTER_API_KEY` | Yes (for `/chat`) | OpenRouter API key for LLM access |
| `JIRA_CLOUD_ID` | Prod only | Cloud ID for OAuth2 API base URL |
| `JIRA_BASE_URL` | Dev only | Jira instance URL (Basic Auth fallback) |
| `JIRA_USER_EMAIL` | Dev only | Email for Basic Auth fallback |
| `JIRA_API_TOKEN` | Dev only | API token for Basic Auth fallback |
| `FRONTEND_URL` | Prod only | CloudFront URL used for CORS and OAuth redirects |
| `CHAT_CLIENT_SERVICE_BASE_URL` | Optional | Base URL of Team 9's chat service for cross-vertical integration |

---

## Running Locally

```bash
export JIRA_OAUTH_CLIENT_ID=...
export JIRA_OAUTH_CLIENT_SECRET=...
export JIRA_OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
export JIRA_BASE_URL=https://myorg.atlassian.net
export JIRA_USER_EMAIL=me@example.com
export JIRA_API_TOKEN=...
export OPENROUTER_API_KEY=...

uvicorn components.jira_service.src.jira_service.main:app --reload
```

---

## Tests

```bash
# All jira_service tests
uv run pytest components/jira_service/ -v

# Unit tests only
uv run pytest components/jira_service/ -m unit
```
