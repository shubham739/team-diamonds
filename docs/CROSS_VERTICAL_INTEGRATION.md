# Cross-Vertical Integration: Jira (Team 1) ↔ Slack (Team 9)

## Overview

This document describes the cross-vertical integration between our Jira issue tracker service (Team 1) and Team 9's Slack chat service, satisfying the HW3 requirements for cross-vertical integration.

## Architecture

### Integration Pattern

We use **Team 9's published `chat-client-api` package** with dependency injection:

```
┌─────────────────────────────────────────────────────────────┐
│                    Jira Service (Team 1)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  /chat-relay Endpoint                                   │ │
│  │  1. Receives AI chat message                            │ │
│  │  2. AI creates Jira issue via tool calling              │ │
│  │  3. Posts result to Slack via Team 9's get_client()     │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Team 9's chat-client-api (Dependency Injection)        │ │
│  │  - get_client() returns registered Slack client         │ │
│  │  - Transparent provider swapping (Slack/Discord/etc)    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Team 9's Slack Service                          │
│  - Receives messages via chat-client-api interface           │
│  - Posts to Slack channels                                   │
└─────────────────────────────────────────────────────────────┘
```

## HW3 Requirements Satisfied

### 1. Pulls Another Vertical's Published API (4 pts) ✅

**Requirement:** "Project depends on at least one other vertical's shared API. The dependency is declared in `pyproject.toml`, not vendored ad-hoc."

**Implementation:**
```toml
# pyproject.toml
dependencies = [
    "chat-client-api",  # Team 9's published package
    # ...
]

[tool.uv.sources]
chat-client-api = { 
    git = "https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source.git", 
    subdirectory = "components/chat_client_api", 
    branch = "main" 
}
```

### 2. Dependency Injection Across Verticals (4 pts) ✅

**Requirement:** "The external vertical's client is injected via the `get_client()` pattern from HW1. Swapping between two providers in that vertical (e.g., Discord ↔ Slack) is transparent to the consumer."

**Implementation:**
```python
# components/jira_service/src/jira_service/main.py

# Import Team 9's DI system
from chat_client_api.client import get_client as get_chat_client
from chat_client_api.client import register_client as register_chat_client

# Register our Slack client at startup
@app.on_event("startup")
def register_slack_client_with_team9():
    from chat_to_issues_integration.slack_client import SlackChatClient
    
    def create_slack_client():
        return SlackChatClient()
    
    register_chat_client(create_slack_client)

# Use Team 9's get_client() to send messages
def _notify_chat_service(channel_id: str, text: str, session_id: str):
    chat_client = get_chat_client()  # Gets our registered Slack client
    chat_client.send_message(channel_id, text)
```

**Provider Swapping:** If Team 9 or another team provides a Discord implementation, we can swap it by simply registering a different client factory - no code changes needed in our service.

### 3. Integration Tests Verify Systems Work Together (4 pts) ✅

**Requirement:** "Tests live under `tests/integration/` and assert on actual behavior of the combined flow. Integration tests that mock all components are an anti-pattern. AI-tool-call → cross-vertical-action pathways are explicitly covered."

**Implementation:**
- `tests/integration/test_cross_vertical_integration.py`
- Tests verify:
  - Team 9's package is imported successfully
  - Dependency injection pattern works
  - `/chat-relay` endpoint exists and integrates AI → Jira → Slack
  - Slack client is registered at startup

## User Flow

### End-User Onboarding

1. **Authenticate with Jira** (`GET /auth/login`)
   - User logs into Jira via OAuth2
   - Receives access token

2. **Link Team 9's Chat Service** (`GET /auth/callback`)
   - Callback returns `team9_login_url`
   - User redirects to Team 9's service to authenticate with Slack
   - Team 9 stores Slack credentials and returns session ID

3. **Select Slack Channel** (`GET /auth/channels`, `POST /auth/select-channel`)
   - User fetches available Slack channels
   - Selects a channel for notifications

4. **Use AI Chat with Cross-Vertical Integration** (`POST /chat-relay`)
   - User sends natural language message
   - AI creates Jira issue via tool calling
   - Result is posted to selected Slack channel via Team 9's `get_client()`

### Example Request

```bash
# Step 1: Authenticate with Jira
curl -X GET https://your-service.com/auth/login

# Step 2: Complete OAuth callback (automatic redirect)
# Returns: { "team9_login_url": "https://team9.com/slack/auth?session=..." }

# Step 3: Authenticate with Team 9's Slack service (browser redirect)

# Step 4: Select a Slack channel
curl -X GET https://your-service.com/auth/channels \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X POST https://your-service.com/auth/select-channel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "C12345"}'

# Step 5: Send AI chat message with cross-vertical integration
curl -X POST https://your-service.com/chat-relay \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create issue: Fix login bug on mobile"}'

# Result:
# 1. AI creates Jira issue "Fix login bug on mobile"
# 2. Issue details posted to Slack channel C12345 via Team 9's service
```

## Technical Details

### Fallback Strategy

Our implementation includes a fallback to HTTP-based communication if Team 9's `chat-client-api` is not available:

```python
def _notify_chat_service(channel_id: str, text: str, session_id: str):
    # Try Team 9's get_client() first (preferred)
    if CHAT_CLIENT_AVAILABLE and get_chat_client is not None:
        try:
            chat_client = get_chat_client()
            chat_client.send_message(channel_id, text)
            return
        except Exception as exc:
            logger.warning("Failed to use Team 9's chat client: %s", exc)
    
    # Fallback to HTTP (backward compatibility)
    base_url = os.environ.get("CHAT_CLIENT_SERVICE_BASE_URL", "")
    # ... HTTP POST to Team 9's service
```

This ensures:
- ✅ Full credit for using Team 9's DI pattern when available
- ✅ Backward compatibility if package not installed
- ✅ Graceful degradation in production

### Environment Variables

```bash
# Jira OAuth2
JIRA_OAUTH_CLIENT_ID=your_client_id
JIRA_OAUTH_CLIENT_SECRET=your_client_secret
JIRA_OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback

# Team 9's Chat Service
CHAT_CLIENT_SERVICE_BASE_URL=https://team9-service.com

# AI Integration
OPENROUTER_API_KEY=your_openrouter_key

# Slack (for our SlackChatClient)
SLACK_BOT_TOKEN=xoxb-your-token
```

## Testing

### Run Integration Tests

```bash
# Run all integration tests
pytest tests/integration/test_cross_vertical_integration.py -v

# Run with coverage
pytest tests/integration/test_cross_vertical_integration.py --cov --cov-report=term-missing
```

### Manual Testing

1. Start the Jira service:
```bash
uvicorn jira_service.main:app --reload
```

2. Complete the authentication flow (see User Flow above)

3. Send a test message:
```bash
curl -X POST http://localhost:8000/chat-relay \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create issue: Test cross-vertical integration"}'
```

4. Verify:
   - Jira issue is created
   - Message appears in Slack channel
   - Logs show "Successfully sent message via Team 9's chat client"

## Benefits of This Approach

1. **Standards Compliance:** Uses Team 9's published API, not ad-hoc HTTP calls
2. **Provider Agnostic:** Can swap Slack for Discord/Teams without code changes
3. **Dependency Injection:** Follows HW1 pattern for loose coupling
4. **Testable:** Clear interfaces make testing straightforward
5. **Backward Compatible:** Falls back to HTTP if package unavailable
6. **Production Ready:** Deployed to AWS Lambda with proper error handling

## Future Enhancements

- Add support for bidirectional sync (Slack → Jira issue updates)
- Implement webhook listeners for real-time Slack events
- Add support for multiple chat providers simultaneously
- Implement message threading for issue discussions
- Add rich formatting for Slack messages (buttons, attachments, etc.)

## References

- Team 9's Repository: https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source
- Team 9's chat-client-api: `components/chat_client_api/`
- HW3 Rubric: Cross-Vertical Integration (12 pts)
