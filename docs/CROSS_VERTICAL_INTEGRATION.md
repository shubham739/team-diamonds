# Cross-Vertical Integration: Jira (Team 1)and Slack (Team 9)

## Overview

This document describes the cross-vertical integration between our Jira service (Team 1) and Team 9's Slack chat service. Our service consumes Team 9's published `chat-client-api` package and integrates it into the `/chat-relay` endpoint, which runs an AI chat loop against Jira and posts the result to a Slack channel via Team 9's DI-based client interface.

## Architecture

```
User / Frontend
     │
     ▼  POST /chat-relay  (Bearer token)
jira-service  (FastAPI on AWS Lambda)
     │
     ├──▶ AI chat loop (OpenRouter LLM + Jira tool calls)
     │         │
     │         ▼
     │    jira-client-impl  →  Jira REST API
     │
     └──▶ _notify_chat_service()
               │
               ├── [primary]  Team 9's get_client().send_message()
               │              via chat-client-api DI system
               │
               └── [fallback] HTTP POST to CHAT_CLIENT_SERVICE_BASE_URL/messages
                              (used if chat-client-api package is unavailable)
```

## How We Use Team 9's `chat-client-api`

### 1. Declared as a dependency in `pyproject.toml`

```toml
[project]
dependencies = [
    "chat-client-api",
    ...
]

[tool.uv.sources]
chat-client-api = {
    git = "https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source.git",
    subdirectory = "components/chat_client_api",
    branch = "main"
}
```

### 2. Imported at startup with a graceful fallback

```python
# components/jira_service/src/jira_service/main.py

try:
    from chat_client_api.client import get_client as get_chat_client
    from chat_client_api.client import register_client as register_chat_client
    CHAT_CLIENT_AVAILABLE = True
except ImportError:
    get_chat_client = None
    register_chat_client = None
    CHAT_CLIENT_AVAILABLE = False
```

If the package is unavailable (e.g. in CI without the dependency), the service falls back to direct HTTP calls. No crash, no broken endpoints.

### 3. Our `SlackChatClient` is registered at app startup

Using Team 9's `register_client()` DI hook, we register a factory for our Slack client during the FastAPI lifespan startup event:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    if CHAT_CLIENT_AVAILABLE and register_chat_client is not None:
        try:
            from chat_to_issues_integration.slack_client import SlackChatClient

            def create_slack_client() -> SlackChatClient:
                return SlackChatClient()

            register_chat_client(create_slack_client)
        except Exception as e:
            logger.warning("Failed to register Slack client with Team 9: %s", e)
    yield
```

This follows the same `get_client()` / `register_client()` dependency injection pattern established in HW1. Swapping Slack for Discord or another provider requires only changing the registered factory — no other code changes.

### 4. Used in `_notify_chat_service()` to send messages

When `/chat-relay` produces a reply, it calls `_notify_chat_service()`, which tries Team 9's DI client first and falls back to HTTP:

```python
def _notify_chat_service(channel_id: str, text: str, session_id: str) -> bool:
    # Primary: Team 9's DI client
    if CHAT_CLIENT_AVAILABLE and get_chat_client is not None:
        try:
            chat_client = get_chat_client()
            chat_client.send_message(channel_id, text)
            return True
        except Exception as exc:
            logger.warning("Falling back to HTTP: %s", exc)

    # Fallback: direct HTTP POST
    base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "").rstrip("/")
    resp = httpx.post(f"{base_url}/messages",
                      json={"channel": channel_id, "text": text},
                      headers={"X-Session-ID": session_id})
    return resp.is_success
```

---

## The `/chat-relay` Endpoint

`POST /chat-relay` is the primary cross-vertical endpoint. It:

1. Resolves the user's session (from in-memory store or DynamoDB — needed because Lambda is stateless)
2. Auto-selects a Team 9 channel if none has been picked yet
3. Runs the AI chat loop (`_run_chat_loop`) — same logic as `/chat`, includes `@jira` tool calling
4. Posts the AI reply to Slack via `_notify_chat_service()`
5. Retries other available channels if the first one fails
6. Returns a login prompt if the Team 9 session needs re-authentication

---

## User Onboarding Flow

Users must connect both Jira and Slack before using `/chat-relay`:

| Step | Endpoint | What Happens |
|------|----------|-------------|
| 1 | `POST /auth/login` `{"action":"get_auth_url","provider":"jira"}` | Get Jira OAuth2 URL |
| 2 | Browser → Atlassian → `GET /auth/callback` | Exchange code for token, create Team 9 chat session, store in DynamoDB |
| 3 | `POST /auth/login` `{"action":"get_auth_url","provider":"slack"}` | Get Slack connect URL |
| 4 | Browser → `GET /auth/callback?state=...` (Slack path) | Create Team 9 chat session, auto-select first available channel |
| 5 | `GET /auth/channels` | List available Team 9 Slack channels |
| 6 | `POST /auth/select-channel` `{"channel_id":"C12345"}` | Store chosen channel in session + DynamoDB |
| 7 | `POST /chat-relay` `{"message":"@jira create issue: Fix bug"}` | AI runs, Jira issue created, reply posted to Slack |

### Example: send a message through the full flow

```bash
# After completing steps 1-6 above:
curl -X POST https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/chat-relay \
  -H "Authorization: Bearer YOUR_JIRA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "@jira create an issue called Fix login bug on mobile"}'

# Response:
# {
#   "reply": "I've created the issue PROJ-99 'Fix login bug on mobile' with status To Do.",
#   "actions": [{"tool": "create_issue", "args": {...}, "result": {...}}]
# }
# The same reply is also posted to the selected Slack channel via Team 9's service.
```

---

## Session Persistence (DynamoDB)

Because the service runs on AWS Lambda (stateless, multiple instances), sessions are persisted to DynamoDB so any Lambda instance can service any request:

- **On `/auth/callback`**: Jira token, Team 9 chat session ID, channel ID, and `team9_login_url` are written to the `team-diamonds-tokens` table (`us-east-2`)
- **On `/chat-relay`**: Session is looked up first from in-memory store, then from DynamoDB, and finally bootstrapped fresh if neither exists (`_get_or_bootstrap_session`)
- **On channel selection**: `_persist_channel_to_dynamodb()` updates the DynamoDB record so the choice survives instance restarts

---

## Deprecated Approaches

Earlier iterations of the cross-vertical integration used different components that are now archived:

- **`components/jira_chat_bridge/`** — a lightweight polling bridge used during cross-team testing; replaced by the direct `chat-client-api` DI integration
- **`components/chat_to_issues_integration/`** — an earlier attempt at a generalized chat+issue bridge; archived once the Team 9 package DI pattern became the standard

Neither component is in the production pipeline.

---

## Environment Variables

| Variable | Description |
|---|---|
| `CHAT_CLIENT_SERVICE_BASE_URL` | Base URL of Team 9's chat service (used for HTTP fallback and channel listing) |
| `TEAM9_CHANNEL_ID` | Optional: hardcode a channel ID to skip auto-selection |
| `OPENROUTER_API_KEY` | Required for the AI chat loop |

---

## Integration Tests

```bash
# Run cross-vertical integration tests
pytest tests/integration/test_cross_vertical_integration.py -v
```

Tests verify:
- Team 9's package imports correctly
- The `register_client` / `get_client` DI pattern works end-to-end
- `/chat-relay` endpoint exists and integrates AI → Jira → Slack
- `SlackChatClient` is registered at startup

## References

- Team 9's Repository: https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source
- Team 9's `chat-client-api`: `components/chat_client_api/`

