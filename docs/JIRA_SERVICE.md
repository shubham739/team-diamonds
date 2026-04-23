# Jira Service (`jira-service`)

## Overview

`jira-service` is the FastAPI deployment unit introduced in HW2. It wraps
`jira-client-impl` over HTTP, exposes an OpenAPI spec, and implements the
full OAuth 2.0 Authorization Code flow so the service can act on behalf of
individual Atlassian users.

## Architecture

```
Consumer (browser / service client)
  │
  ▼  HTTP (Bearer token)
jira-service  (FastAPI)
  │
  ▼  Python function call
jira-client-impl  (JiraClient)
  │
  ▼  HTTPS (Basic Auth or OAuth2 Bearer)
Jira REST API v3 / Atlassian API
```

## Authentication

## Authentication

The service supports two authentication strategies, chosen based on environment configuration:

#### OAuth2 Bearer Token Path (Production, Multi-User)
When `JIRA_CLOUD_ID` is set, the service uses Atlassian OAuth2 bearer tokens for Jira API access. This enables multi-user deployments where each request carries a per-user access token obtained via the OAuth2 Authorization Code flow.

The standard web-server OAuth 2.0 flow is implemented:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login` | GET | Redirect browser to Jira's authorization URL |
| `/auth/callback` | GET | Receive code, exchange for tokens, store session |
| `/auth/logout` | GET | Invalidate session |

Tokens are stored server-side in an in-memory session dict (keyed by `account_id`) for refresh purposes. The client receives a bearer token it passes on subsequent requests via `Authorization: Bearer <token>`.

#### Basic Auth Fallback Path (Development, Single-User)
When `JIRA_CLOUD_ID` is not set, the service falls back to Basic Auth using `JIRA_USER_EMAIL` and `JIRA_API_TOKEN`. This is the single-developer path and is also used when the Bearer token in the request header is not a user session token but rather a service-level API token.

In both paths, the FastAPI dependency `get_jira_client` selects the appropriate JiraClient instance based on available environment variables.

## Endpoints

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | No | Returns `{"status": "ok"}` — used by deployment health checks |
| `GET` | `/auth/login` | No | Initiates OAuth2 flow |
| `GET` | `/auth/callback` | No | OAuth2 callback (called by Atlassian) |
| `GET` | `/auth/logout` | No | Clears user session |
| `GET` | `/` | Yes | Fetch 5 most-recent issues |
| `GET` | `/issues` | Yes | List issues with optional filters |
| `GET` | `/issues/{issue_id}` | Yes | Fetch a single issue |
| `POST` | `/issues` | Yes | Create a new issue (JSON body) |
| `PUT` | `/issues/{issue_id}` | Yes | Update an issue (JSON body, partial update) |
| `DELETE` | `/issues/{issue_id}` | Yes | Delete an issue |

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_OAUTH_CLIENT_ID` | Yes | Atlassian OAuth2 app client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | Yes | Atlassian OAuth2 app client secret |
| `JIRA_OAUTH_REDIRECT_URI` | Yes | Must match the callback URL registered in Atlassian |
| `JIRA_CLOUD_ID` | Prod only | Cloud ID for OAuth2 API base URL. Obtain from `/oauth/token/accessible-resources` |
| `JIRA_BASE_URL` | Dev only | Jira instance URL (Basic Auth fallback, e.g. `https://myorg.atlassian.net`) |
| `JIRA_USER_EMAIL` | Dev only | Email for Basic Auth fallback |
| `JIRA_API_TOKEN` | Dev only | API token for Basic Auth fallback |

> **Production vs development:** When `JIRA_CLOUD_ID` is set the service uses
> OAuth2 Bearer tokens for Jira API calls (multi-user, production path).
> When it is absent the service falls back to Basic Auth using
> `JIRA_USER_EMAIL` / `JIRA_API_TOKEN` (single-developer / CI path).

## Running Locally

```bash
# Set environment variables (or add to .venv/.env)
export JIRA_OAUTH_CLIENT_ID=...
export JIRA_OAUTH_CLIENT_SECRET=...
export JIRA_OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
export JIRA_BASE_URL=https://myorg.atlassian.net
export JIRA_USER_EMAIL=me@example.com
export JIRA_API_TOKEN=...

uvicorn components.jira_service.src.jira_service.main:app --reload
```

The interactive API docs are then available at `http://localhost:8000/docs`.

## Tests

Integration tests live at
`components/jira_service/tests/integration/test_api.py` and use FastAPI's
`TestClient` — no live server required.

```bash
pytest components/jira_service/ -v
```
