
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

- components/
    - api (external dependency)                                    # Vendor-neutral interfaces and shared domain models.
    - jira_client_impl/                                           # Direct Jira client implementation (local/library path).
    - jira_service/                                               # FastAPI service exposing Jira operations over HTTP.
    - jira_service_api_client/                                    # Typed HTTP client for the service API.
    - jira_service_adapter/                                       # Adapter that implements the common interface using the service client.

- tests/
    - unit/                                                       # Unit test suite.
    - integration/                                                # Integration tests (including live Jira scenarios in CI contexts).
    - e2e/                                                        # End-to-end workflow tests.

- docs/
    - Architecture, component docs, contribution guidance, and implementation notes.

- Root config/infrastructure
    - Workspace/tooling config, CI pipeline, container/deployment config, and project metadata.


---

## How It Works

The project uses a layered architecture for location transparency:

| Layer | Package | Purpose |
|-------|---------|---------|
| 1 | `api` | External contract package — defines what a client does |
| 2 | `jira-client-impl` | Local Jira implementation — calls Jira REST API directly |
| 3 | `jira-service` | FastAPI service — exposes layer 2 over HTTP |
| 4 | `jira-service-api-client` | Type-safe HTTP client for the FastAPI service |
| 5 | `jira-service-adapter` | Adapter — wraps layer 4 behind the layer 1 interface |

Consumers use the same `get_client()` call for local or remote access.

```python
# Option A — local library
from jira_client_impl import get_client

# Option B — remote service
from jira_service_adapter import get_client

client = get_client()   # same interface, same call sites
```

---

## Deployment

The FastAPI service is deployed as a Docker container via AWS Lambda.

| Item | Value |
|------|-------|
| Platform | AWS Lambda |
| Service URL | Configured via AWS Lambda and API Gateway |
| OAuth Redirect URI | Configured via `JIRA_OAUTH_REDIRECT_URI` environment variable for OAuth callback handling |
| Health check | `GET /health` → `{"status": "ok"}` |
| OpenAPI spec | `GET /openapi.json` |
| Interactive docs | `GET /docs` |

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
