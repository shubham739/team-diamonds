
# Team Diamonds

### Team Members
* Subhradeep Acharjee
* Ethan Bell
* Shubham Tanwar
* Tanya Thomas
* Conor Zhang

---

## Overview

Team Diamonds is a Jira issue management service with an AI-powered chat interface, deployed on AWS Lambda. It exposes a REST API for creating, reading, updating, and deleting Jira issues, and a natural-language chat endpoint backed by an LLM (OpenRouter). It also integrates cross-vertically with Team 9's Slack service, allowing AI-generated replies to be posted directly to a user's Slack channel.

The interface layer is provided by the external `ospd-issue-tracker-api` package, which defines vendor-neutral ABCs (`IssueTrackerClient`, `Issue`, `Status`). The Jira implementation lives in `jira_client_impl`, and the deployed FastAPI application lives in `jira_service`.

---

## Motivation

Modern work is spread across many tools — issue trackers, inboxes, chat apps,
pull requests. Keeping track of everything requires constant context switching.
This assistant aims to bring those sources together so that managing your work
feels seamless, regardless of which platforms your team uses.

---

## Repository Structure

Only production components are shown. Deprecated components (`jira_service_adapter`, `jira_service_api_client`, `work_mgmt_client_interface`, `jira_chat_bridge`, `chat_to_issues_integration`) remain in the repo but are not part of the live deployment.

```
├── components/
│   ├── chat_to_issues_integration/           # Only slack_client.py is used in production
│   │   └── src/
│   │       └── chat_to_issues_integration/
│   │           └── slack_client.py           # Provides SlackChatClient — registered at startup in jira_service
│   │
│   ├── jira_client_impl/                     # Jira implementation (Basic Auth + OAuth2)
│   │   ├── src/
│   │   │   └── jira_client_impl/
│   │   │       ├── jira_board.py
│   │   │       ├── jira_impl.py
│   │   │       └── jira_issue.py
│   │   └── tests/
│   │       └── test_core_methods.py
│   │
│   └── jira_service/                         # FastAPI service — deployed on AWS Lambda via Mangum
│       ├── src/
│       │   └── jira_service/
│       │       ├── ai_client_api.py          # AI chat loop (OpenRouter / llm-integration-api)
│       │       ├── auth.py                   # OAuth2 + DynamoDB session management
│       │       ├── exceptions.py
│       │       ├── handler.py                # Issue CRUD route handlers
│       │       └── main.py                   # FastAPI app, startup, Team 9 DI registration
│       └── tests/
│           ├── test_ai_client_api.py
│           ├── test_auth.py
│           ├── test_handler.py
│           ├── test_main_helpers.py
│           └── integration/                  # Cross-vertical integration tests (Team 9)
│
├── tests/
│   ├── e2e/                                  # End-to-end tests (real Jira API, skipped without creds)
│   │   └── test_client_e2e.py
│   └── integration/                          # Integration tests (CI-gated)
│       └── test_client_integration.py
│
├── docs/                                     # MkDocs documentation source
├── frontend/                                 # React frontend (served via CloudFront)
├── .circleci/config.yml                      # CI/CD pipeline
├── Dockerfile                                # Production Docker image
├── pyproject.toml                            # Root uv workspace + ruff / mypy / pytest config
└── README.md
```


---

## How It Works

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

| Component | Role |
|---|---|
| `ospd-issue-tracker-api` | External package — defines `IssueTrackerClient` ABC, `Issue` ABC, `Status` enum |
| `jira-client-impl` | Implements the ABC against Jira REST API v3; supports OAuth2 and Basic Auth |
| `jira-service` | FastAPI app deployed on Lambda; handles issue CRUD, AI chat, and Team 9 relay |
| `llm-integration-api` | Wraps OpenRouter; provides the AI chat loop with Jira tool definitions |
| `chat-client-api` (Team 9) | DI interface for posting messages to Team 9's Slack service |
| DynamoDB | Persists OAuth tokens and Team 9 session IDs across stateless Lambda instances |

---

## Deployment

The FastAPI service is deployed on AWS Lambda via Mangum, behind API Gateway. Session state is persisted in DynamoDB so multiple Lambda instances can serve the same user.

| Item | Value |
|---|---|
| Platform | AWS Lambda + API Gateway |
| Live API docs | `https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod/docs` |
| Health check | `GET /health` → `{"status": "ok"}` |
| Session store | DynamoDB table `team-diamonds-tokens` (`us-east-2`) |

### Required Environment Variables

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

---

## CI/CD Pipeline (CircleCI)

The CircleCI pipeline runs on every push and is **publicly visible**.

**All branches except `main`:**
```
build → lint → unit_test → circleci_test → report_summary
```

**`main` branch only:**
```
build → lint → unit_test → circleci_test → integration_test → deploy → report_summary
```

| Job | Description |
|---|---|
| `build` | Installs uv + all workspace dependencies |
| `lint` | Runs `ruff check .` |
| `unit_test` | Runs component unit tests, enforces 85% coverage, runs mypy |
| `circleci_test` | Runs all tests not requiring local credentials |
| `integration_test` | Runs integration tests against the live Jira API (requires `jira-client` context; `main` only) |
| `deploy` | Deploys to AWS Lambda (requires `aws-deploy` context; `main` only) |
| `report_summary` | Aggregates test and coverage report artifacts |

---

## Quick Start (Local Development)

```bash
git clone https://github.com/shubham739/team-diamonds.git
cd team-diamonds

# Install all workspace packages + dev tools
uv sync --all-packages --extra dev

# Copy and fill in your credentials
cp .venv/.env.example .venv/.env   # edit with your values

# Run the service
uvicorn components.jira_service.src.jira_service.main:app --reload

# Run all tests
pytest

# Type-check
mypy components/

# Lint
ruff check .
```

---

## Further Reading

- [Design & Architecture](DESIGN.md)
- [Deployment Overview](DEPLOYMENT_OVERVIEW.md)
- [Jira Service](JIRA_SERVICE.md)
- [Jira Client Implementation](JIRA_CLIENT_IMPLEMENTATION.md)
- [Cross-Vertical Integration (Team 9)](CROSS_VERTICAL_INTEGRATION.md)
- [Contributing Guide](CONTRIBUTING.md)
