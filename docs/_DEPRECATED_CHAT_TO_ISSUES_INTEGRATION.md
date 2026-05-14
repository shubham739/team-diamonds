# [DEPRECATED] Chat-to-Issues Integration

> **DEPRECATED — This component is mostly archived and no longer in active use.**
>
> **Exception:** `slack_client.py` (`SlackChatClient`) is still actively used.
> `jira_service/main.py` imports `SlackChatClient` during its `lifespan()` startup
> and registers it with Team 9's DI registry (`chat_client_api`). This allows
> `jira_service` to send Slack notifications via `_notify_chat_service()` without
> depending on the rest of this component. Only `slack_client.py` should be
> considered live; everything else in this package is archived.

This component bridged a **chat platform** (Slack, Discord, Telegram) with an **issue tracker** (Jira, Trello), allowing chat messages to be converted into tracked issues and issue summaries to be posted back to chat channels. It followed a dependency-injection pattern so any `ChatClient` and `IssueTrackerClient` could be swapped in without code changes.

The `slack_bot_server.py` entry point and the `IntegrationApp` wiring are no longer deployed. The component is retained here for reference, with the exception of `slack_client.py` noted above.

## Running Tests

```bash
pytest components/chat_to_issues_integration/tests/ -v
```

All tests use `MockChatClient` and mock trackers — no external dependencies required.

## Dependencies

- `ospd-issue-tracker-api` — shared issue tracker interface
- `jira-service-adapter` — Jira implementation (workspace member)
- `slack-sdk` — Slack API client (for production Slack impl)
