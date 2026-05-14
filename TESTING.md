# HW3 Cross-Vertical Integration Testing

> **Note:** For general testing instructions, see the main [README.md](README.md#testing-infrastructure).  
> This document focuses specifically on **HW3 cross-vertical integration** testing.

## Quick Start

### 1. Install Dependencies
```bash
uv sync --extra dev
```

### 2. Run Cross-Vertical Integration Tests
```bash
# Activate virtual environment (Windows)
.venv\Scripts\Activate.ps1

# Run HW3 cross-vertical integration tests
pytest tests/integration/test_cross_vertical_integration.py -v
```

### 3. Start the Service
```bash
uv run uvicorn jira_service.main:app --reload --port 8000
```

## Test Results

**Status:** All tests passing (5 passed, 1 skipped)

See [docs/TESTING_RESULTS.md](docs/TESTING_RESULTS.md) for detailed results.

## HW3 Requirements - All Satisfied

| Requirement | Points | Status | Test |
|-------------|--------|--------|------|
| Pulls another vertical's published API | 4 | PASS | `test_team9_chat_client_api_imported` |
| Dependency Injection across verticals | 4 | PASS | `test_dependency_injection_pattern` |
| Integration tests verify systems work | 4 | PASS | `test_chat_relay_endpoint_exists` |
| **Total** | **12** | **PASS** | **5 tests passing** |

## Key Files

- **Dependency:** `pyproject.toml` - Team 9's `chat-client-api` package
- **Implementation:** `components/jira_service/src/jira_service/main.py` - DI registration and usage
- **Tests:** `tests/integration/test_cross_vertical_integration.py` - Integration tests
- **Documentation:** `docs/CROSS_VERTICAL_INTEGRATION.md` - Full technical documentation

## Environment Variables

Required in `.env` file (project root):

```bash
# Slack (for cross-vertical integration with Team 9)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_USER_ID=your-bot-user-id

# Team 9's Chat Service
CHAT_CLIENT_SERVICE_BASE_URL=https://team9-service.com

# Jira credentials (see README.md for details)
JIRA_BASE_URL=https://your-instance.atlassian.net
JIRA_USER_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

## Documentation

- [TESTING_RESULTS.md](docs/TESTING_RESULTS.md) - Detailed test results and verification
- [CROSS_VERTICAL_INTEGRATION.md](docs/CROSS_VERTICAL_INTEGRATION.md) - Technical documentation
- [TESTING_SESSION_SUMMARY.md](docs/TESTING_SESSION_SUMMARY.md) - Testing session notes

## Troubleshooting

### "Slack token required" error
**Solution:** Ensure `SLACK_BOT_TOKEN` is set in `.env` file in project root.

### Test skipped: "OPENROUTER_API_KEY not set"
**Status:** Expected - AI integration test is optional and requires an API key.

### For other issues
See the main [README.md](README.md#testing-infrastructure) for general testing troubleshooting.
