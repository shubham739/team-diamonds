
# Team Diamonds

### Team Members
* Subhradeep Acharjee
* Ethan Bell
* Shubham Tanwar
* Tanya Thomas
* Conor Zhang

---

## Overview

This project is an AI assistant designed to help people manage their tasks and
to-dos from a variety of sources in one place. Rather than switching between
tools, the assistant connects to the platforms people already use and provides a
unified interface for managing work.

The first integration is issue trackers (starting with Jira), with plans to
expand to email, messaging, and code reviews over time.

---

## Motivation

Modern work is spread across many tools — issue trackers, inboxes, chat apps,
pull requests. Keeping track of everything requires constant context switching.
This assistant aims to bring those sources together so that managing your work
feels seamless, regardless of which platforms your team uses.

---

## Repository Structure

```
├── components/
│   ├── work_mgmt_client_interface/   # Vendor-neutral interface contracts (ABC)
│   │   ├── src/
│   │   └── README.md
│   │
│   ├── jira_client_impl/             # Local Jira implementation (Basic Auth + OAuth2)
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── jira_service/                 # FastAPI microservice (HW2)
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── jira_service_api_client/      # Type-safe HTTP client for jira-service (HW2)
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   │
│   └── jira_service_adapter/         # Adapter: IssueTrackerClient over HTTP (HW2)
│       ├── src/
│       ├── tests/
│       └── README.md
│
├── tests/
│   ├── integration/                  # Integration tests (real Jira API, CI-gated)
│   └── e2e/                          # End-to-end tests
│
├── docs/                             # MkDocs documentation source
├── .circleci/config.yml              # CI/CD pipeline
├── Dockerfile                        # Production Docker image
├── render.yaml                       # Render.com deployment config
├── openapi.json                      # OpenAPI 3.1.0 spec (auto-generated from service)
├── makefile                          # Developer helpers (install, generate-client)
└── pyproject.toml                    # Root uv workspace + ruff / mypy / pytest config
```

---

## How It Works

The project is split into five layers (HW1 introduced layers 1–2; HW2 added 3–5):

| Layer | Package | Purpose |
|-------|---------|---------|
| 1 | `work-mgmt-client-interface` | Abstract contract — defines *what* a client does |
| 2 | `jira-client-impl` | Local Jira implementation — calls Jira REST API directly |
| 3 | `jira-service` | FastAPI service — exposes layer 2 over HTTP with OAuth2 |
| 4 | `jira-service-api-client` | Type-safe HTTP client for the FastAPI service |
| 5 | `jira-service-adapter` | Adapter — wraps layer 4 behind the layer 1 interface |

**Location transparency:** Layers 2 and 5 both implement the same
`IssueTrackerClient` ABC, so consumer code (e.g. `main.py`) is identical
regardless of which path is chosen:

```python
# Option A — local library
from jira_client_impl import get_client

# Option B — remote service
from jira_service_adapter import get_client

client = get_client()   # same interface, same call sites
```

---

## Deployment

The FastAPI service is deployed on **Render.com** (Docker, free plan).

| Item | Value |
|------|-------|
| Platform | Render.com |
| Deployment URL | `https://team-diamonds.onrender.com` |
| Health check | `GET /team-diamonds.onrender.com/health` → `{"status": "ok"}` |
| OpenAPI spec | `https://team-diamonds.onrender.com/openapi.json` |
| Interactive docs | `https://team-diamonds.onrender.com/docs` |

### Environment Variables (set via Render Secrets — never committed)

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_OAUTH_CLIENT_ID` | Yes | Atlassian OAuth2 app client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | Yes | Atlassian OAuth2 app client secret |
| `JIRA_OAUTH_REDIRECT_URI` | Yes | OAuth callback URL registered in Atlassian |
| `JIRA_CLOUD_ID` | Prod | Cloud ID for OAuth2 Jira API base. From `/oauth/token/accessible-resources` |
| `JIRA_BASE_URL` | Dev/CI | Jira instance URL for Basic Auth fallback |
| `JIRA_USER_EMAIL` | Dev/CI | Atlassian account email for Basic Auth |
| `JIRA_API_TOKEN` | Dev/CI | API token from Atlassian account settings |

### OAuth2 Redirect URIs

Register **both** of the following in your Atlassian OAuth2 app settings:

- **Local:** `http://localhost:8000/auth/callback`
- **Production:** `https://team-diamonds.onrender.com/auth/callback`

Use the `JIRA_OAUTH_REDIRECT_URI` environment variable to select the correct
one at runtime.

---

## CI/CD Pipeline (CircleCI)

The CircleCI pipeline runs on every push and is **publicly visible**.

```
build → lint → unit_test → circleci_test → deploy (hw2 branch only)
                                        └── report_summary
```

| Job | Description |
|-----|-------------|
| `build` | Installs uv + all workspace dependencies |
| `lint` | Runs `ruff check .` |
| `unit_test` | Runs component unit tests, enforces 85% coverage, runs mypy |
| `circleci_test` | Runs all tests not requiring local credentials |
| `deploy` | Triggers Render deploy hook (hw2 branch only, after tests pass) |
| `report_summary` | Aggregates test and coverage report artifacts |

Full integration tests against the live Jira API run only on `main` via the
`full_integration` workflow using the `jira-client` CircleCI context.

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
- [Jira Service](JIRA_SERVICE.md)
- [Jira Service API Client](JIRA_SERVICE_API_CLIENT.md)
- [Jira Service Adapter](JIRA_SERVICE_ADAPTER.md)
- [Interface Contract](INTERFACE.md)
- [Contributing Guide](CONTRIBUTING.md)
