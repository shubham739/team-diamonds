# Chat-to-Issues Integration

Cross-vertical integration component that bridges a **chat platform** (Slack, Discord, Telegram) with an **issue tracker** (Jira, Trello).

## Architecture

This component follows the **dependency injection** pattern — it accepts any `ChatClient` and any `IssueTrackerClient` at runtime, so:

- **Jira + Slack** → production
- **Jira + Mock** → local dev / testing  
- **Trello + Discord** → another team's setup, zero code changes

## Components

### `ChatClient` (ABC)
Abstract interface for any chat platform. Defines:
- `get_channels()`, `get_channel(id)`
- `get_messages(channel_id, limit)`, `get_message(id)`
- `send_message(channel_id, text)`, `delete_message(id)`

### `MockChatClient`
Fully in-memory implementation for local development and testing. Each instance maintains isolated state — instantiate one per user to guarantee no cross-user data leakage.

### `IntegrationApp`
The core integration logic. Wires a tracker client and a chat client together via dependency injection.

**Key methods:**
- `post_issues_to_channel(channel_id)` — fetch issues and post summaries to chat
- `post_issue_to_channel(issue_id, channel_id)` — post a single issue
- `create_issue_from_message(message_id)` — turn a chat message into an issue
- `create_issue_from_channel_latest(channel_id)` — create issue from latest message

## Usage

### Local Development (Mock Chat)

```python
from chat_to_issues_integration import IntegrationApp, MockChatClient
from jira_service_adapter.adapter import get_client as get_tracker_client

# Set up clients
tracker = get_tracker_client()  # uses env vars for Jira service
chat = MockChatClient(user_id="alice")
channel = chat.add_channel("general")

# Wire them together
app = IntegrationApp(tracker_client=tracker, chat_client=chat)

# Post issues to chat
app.post_issues_to_channel(channel.id, max_results=10)

# Create issue from chat message
msg = chat.send_message(channel.id, "Add export to CSV")
issue = app.create_issue_from_message(msg.id)
```

### Production (Real Slack)

When ready for real Slack integration:

1. Implement `SlackChatClient(ChatClient)` using `slack-sdk`
2. Swap it in at the injection site:

```python
from chat_to_issues_integration import IntegrationApp
from slack_chat_client import SlackChatClient  # your impl
from jira_service_adapter.adapter import get_client as get_tracker_client

tracker = get_tracker_client()
chat = SlackChatClient(token=user_slack_token)  # per-user token

app = IntegrationApp(tracker_client=tracker, chat_client=chat)
# All IntegrationApp methods work identically
```

## User Isolation

Each `IntegrationApp` instance is scoped to **one user**:

```python
# User A
tracker_a = get_tracker_client_for_user("alice")
chat_a = SlackChatClient(token=alice_token)
app_a = IntegrationApp(tracker_a, chat_a)

# User B
tracker_b = get_tracker_client_for_user("bob")
chat_b = SlackChatClient(token=bob_token)
app_b = IntegrationApp(tracker_b, chat_b)

# app_a and app_b share zero state
```

This is the same pattern used in `jira_service` with FastAPI dependency injection.

## Running the Demo

```bash
python components/chat_to_issues_integration/demo.py
```

## Running Tests

```bash
pytest components/chat_to_issues_integration/tests/ -v
```

All tests use `MockChatClient` and mock trackers — no external dependencies required.

## Next Steps

1. **Implement `SlackChatClient`** — concrete Slack impl using `slack-sdk`
2. **Deploy as FastAPI service** — expose `IntegrationApp` methods as HTTP endpoints
3. **Add AI client** — integrate OpenAI/Claude for intelligent issue triage
4. **Telemetry** — add request latency and success/failure rate tracking

## Dependencies

- `ospd-issue-tracker-api` — shared issue tracker interface
- `jira-service-adapter` — Jira implementation (workspace member)
- `slack-sdk` — Slack API client (for production Slack impl)
