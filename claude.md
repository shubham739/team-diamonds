# CLAUDE.md — Team Diamonds

## 1. Project Overview

**Team Diamonds** is a vendor-neutral Python microservice that exposes a unified HTTP API for managing work items (issues, tasks) across multiple platforms. Currently integrates with **Jira Cloud**; designed to be extended with Linear, GitHub Issues, etc.

**Key Components:**
- `work_mgmt_client_interface` — Abstract contracts (ABCs) defining the vendor-neutral API surface
- `jira_client_impl` — Concrete Jira integration: REST API v3, OAuth2, JQL, ADF, status transitions
- `main.py` — FastAPI application exposing HTTP endpoints
- `auth.py` — OAuth2 token exchange, refresh, and in-memory session management

**Architectural pattern:** Interface/Implementation split. Application code only imports from the interface package; concrete implementations register via `get_client()`. This allows adding new platform integrations without changing callers.

---

## 2. Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.12+ |
| Package manager | `uv` (Astral) — workspace-aware, replaces pip/Poetry |
| Web framework | FastAPI 0.100+ |
| ASGI server | Uvicorn 0.41.0+ |
| HTTP client | `requests` 2.31+ |
| Auth | `authlib` 1.2+ (OAuth2) |
| Env config | `python-dotenv` |
| Linting + formatting | `ruff` 0.12.7+ (replaces black, flake8, isort) |
| Type checking | `mypy` 1.17+ (strict mode) |
| Testing | `pytest` 8.4.1+ with `pytest-cov`, `pytest-mock` |
| Docs | MkDocs + Material theme + mkdocstrings |
| CI/CD | CircleCI 2.1 |

---

## 3. Repository Structure

```
.
├── main.py                          # FastAPI app — routes + OAuth flow (lenient lint rules)
├── auth.py                          # OAuth2: token exchange, refresh, in-memory sessions
├── conftest.py                      # Pytest root config (adds components/ to sys.path)
├── pyproject.toml                   # Root uv workspace + ruff/mypy/pytest config
├── uv.lock                          # Pinned dependency graph (commit this)
├── makefile                         # install, generate-client, setup targets
├── openapi.json                     # Generated OpenAPI spec (from running server)
├── mkdocs.yml                       # MkDocs documentation config
│
├── components/
│   ├── work_mgmt_client_interface/  # ABCs and contracts — DO NOT add Jira-specific logic here
│   │   └── src/work_mgmt_client_interface/
│   │       ├── client.py            # IssueTrackerClient ABC, get_client() factory stub
│   │       ├── issue.py             # Issue ABC, Status enum, IssueUpdate dataclass
│   │       └── board.py             # Board ABC, BoardColumn dataclass
│   │
│   └── jira_client_impl/            # Jira concrete implementation — all Jira specifics live here
│       ├── src/jira_client_impl/
│       │   ├── jira_impl.py         # JiraClient, JQL builder, _get/_post, sanitize_input
│       │   ├── jira_issue.py        # JiraIssue, ADF parser, _normalize_status, build_issue
│       │   └── jira_board.py        # JiraBoard (delegates to JiraClient)
│       └── tests/
│           └── test_core_methods.py # Unit tests for all jira_client_impl logic
│
├── tests/
│   ├── integration/                 # Require real Jira credentials (not run in most CI)
│   └── e2e/                         # Full workflow tests (require credentials)
│
└── docs/                            # MkDocs source (README, DESIGN, CONTRIBUTING, API docs)
```

---

## 4. Coding Guidelines

### Naming Conventions

| Construct | Convention | Examples |
|---|---|---|
| Classes | `PascalCase` | `JiraClient`, `IssueTrackerClient`, `Status` |
| Functions/methods | `snake_case` | `get_client()`, `build_issue()`, `sanitize_input()` |
| Private/internal | `_snake_case` | `_get()`, `_post()`, `_build_jql_query()` |
| Module-level constants | `SCREAMING_SNAKE_CASE` | `_API_PREFIX`, `_STATUS_TO_JQL`, `HTTP_OK` |
| Enums | `PascalCase` class, `UPPER` members | `Status.TODO`, `Status.IN_PROGRESS` |
| Dataclasses | `PascalCase` | `IssueUpdate`, `BoardColumn` |
| Test functions | `test_[feature]_[scenario]` | `test_status_happy_path`, `test_update_issue_title_sa` |
| Test fixtures | `snake_case` | `jira_client`, `jira_board`, `created_issue` |

### Style Rules

- **Line length:** 130 characters (ruff enforced)
- **Python version:** Use `str | None` union syntax (not `Optional[str]`), `dict[str, Any]` (not `Dict`)
- **Type hints:** All function signatures must be fully typed — mypy strict mode is enforced
- **Docstrings:** Required on public classes and methods; Google-style with Args/Returns/Raises
- **Imports:** ruff isort manages ordering automatically; `known-first-party` includes `jira_client_impl` and `work_mgmt_client_interface`
- **Enums:** Use `StrEnum` for string enums (see `Status`)
- **Dataclasses:** Use `@dataclass` for plain data structures like `IssueUpdate`

### Do's

- **Do** import from `work_mgmt_client_interface` in application code — never import `jira_client_impl` directly in `main.py` except to register the factory
- **Do** use `sanitize_input()` on any user-supplied string before injecting into JQL queries
- **Do** use `IssueUpdate` for partial updates — only non-`None` fields are applied
- **Do** map status changes via `_STATUS_TO_JIRA_TRANSITION` — Jira requires transition IDs, not direct field edits
- **Do** convert ADF to plain text via `_extract_adf_text()` on read; convert plain text to ADF via `_text_to_adf()` on write
- **Do** mark all tests with the appropriate pytest marker (`unit`, `integration`, `e2e`, `circleci`, `local_credentials`)
- **Do** write `TYPE_CHECKING` guards for imports used only in type annotations to avoid circular imports

### Don'ts

- **Don't** add Jira-specific logic to `work_mgmt_client_interface` — that package must stay platform-agnostic
- **Don't** hardcode credentials — all secrets must come from environment variables or dotenv
- **Don't** use `Optional[X]` — prefer `X | None`
- **Don't** skip type annotations — mypy strict will fail the CI build
- **Don't** add bare `except:` clauses — catch specific exceptions
- **Don't** store tokens or sessions in anything other than the in-memory `user_sessions` dict (no DB, no files — deliberate MVP constraint)
- **Don't** edit `main.py` assuming ruff/mypy rules apply equally — it is excluded from both tools intentionally
- **Don't** commit the `jira_service_api_client/` directory — it is gitignored (generated code)

---

## 5. Development Workflow

### Initial Setup

```bash
uv sync                             # Install all workspace packages + dev extras
source .venv/bin/activate           # Activate venv
# Populate .env with: JIRA_OAUTH_CLIENT_ID, JIRA_OAUTH_CLIENT_SECRET, JIRA_OAUTH_REDIRECT_URI
```

### Running the Server

```bash
uv run uvicorn main:app --reload    # Dev server at http://localhost:8000
# Swagger UI:   http://localhost:8000/docs
# ReDoc:        http://localhost:8000/redoc
```

### Linting & Formatting

```bash
uv run ruff check .                                   # Lint
uv run ruff format .                                  # Auto-format
uv run mypy components/ --explicit-package-bases      # Type check
```

Run all three before committing. CI will fail on any ruff or mypy errors.

### Running Tests

```bash
# Unit tests only (fast, no credentials needed)
uv run pytest components/ -m unit

# All tests safe for CI (no local credentials required)
uv run pytest -m "not local_credentials"

# With coverage (must meet 85% threshold)
uv run pytest components/ --cov=components --cov-report=term-missing --cov-fail-under=85

# Full test suite (requires Jira credentials in environment)
uv run pytest

# CircleCI-compatible subset
uv run pytest -m circleci
```

### Generating the OpenAPI Client

```bash
make generate-client   # Starts server, fetches spec, runs openapi-python-client
# Output: jira_service_api_client/ (gitignored — do not hand-edit)
```

### Documentation

```bash
uv run mkdocs serve    # Serve docs at http://localhost:8000
uv run mkdocs build    # Build static site
```

---

## 6. API & Service Patterns

### Endpoint Conventions

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — no auth required |
| `GET` | `/auth/login` | Redirect to Jira OAuth2 consent |
| `GET` | `/auth/callback` | OAuth2 callback — stores token |
| `GET` | `/auth/logout` | Clear session |
| `GET` | `/issues` | List issues (with optional filters) |
| `GET` | `/issues/{issue_id}` | Get single issue |
| `POST` | `/issues` | Create issue |
| `PUT` | `/issues/{issue_id}` | Update issue (partial) |
| `DELETE` | `/issues/{issue_id}` | Delete issue |

### Request/Response Conventions

- Authentication: `Depends(oauth2_scheme)` — Bearer token from OAuth2 flow
- Query params for filters: `title`, `description`, `status`, `assignee`, `due_date`, `max_results`
- Path params for IDs: `{issue_id}` (Jira key format, e.g. `PROJ-123`)
- Response format: JSON dict with fields: `id`, `title`, `description`, `status`, `assignee`, `due_date`

### Error Handling Patterns

```python
raise HTTPException(status_code=404, detail="Issue not found")
raise HTTPException(status_code=401, detail="No valid session found")
raise HTTPException(status_code=400, detail="Invalid status value")
raise HTTPException(status_code=503, detail="Jira service unavailable")
```

Custom exceptions from `jira_client_impl`:
- `JiraError` — general Jira API errors
- `IssueNotFoundError` — wraps `BaseIssueNotFoundError` from the interface layer

### Status Mapping

Platform statuses are normalized to four canonical values:

| `Status` enum | Meaning |
|---|---|
| `Status.TODO` | Not started |
| `Status.IN_PROGRESS` | Active work |
| `Status.COMPLETE` | Done |
| `Status.CANCELLED` | Dropped |

Use `_normalize_status()` in `jira_issue.py` when parsing Jira responses. Use `_STATUS_TO_JIRA_TRANSITION` in `jira_impl.py` when writing status changes (must go through Jira's Transitions API).

### OAuth2 Flow

Jira uses a redirect-based OAuth mechanism — not standard Authorization Code flow. Tokens are stored per-user in the in-memory `user_sessions` dict in `auth.py`. Always use `get_valid_token(user_id)` (not raw dict access) to ensure automatic refresh on expiry.

---

## 7. Testing Guidelines

### Test Markers

| Marker | When to use |
|---|---|
| `@pytest.mark.unit` | Isolated, fully mocked — no network, no credentials |
| `@pytest.mark.integration` | Real Jira API, requires credentials |
| `@pytest.mark.e2e` | Full system workflow, requires credentials |
| `@pytest.mark.circleci` | Safe to run in CI without local credentials |
| `@pytest.mark.local_credentials` | Requires `JIRA_API_TOKEN` etc. — skipped in most CI |

Every test function must have at least one marker.

### Writing Unit Tests

```python
import pytest
from unittest.mock import MagicMock

@pytest.mark.unit
@pytest.mark.circleci
class TestJiraClientGetIssue:
    def test_returns_issue_on_success(self, jira_client: JiraClient) -> None:
        jira_client._get.return_value = {...}  # Mock HTTP response
        result = jira_client.get_issue("PROJ-1")
        assert result.id == "PROJ-1"

    def test_raises_not_found_on_404(self, jira_client: JiraClient) -> None:
        jira_client._get.side_effect = IssueNotFoundError("PROJ-1")
        with pytest.raises(IssueNotFoundError):
            jira_client.get_issue("PROJ-1")
```

### Best Practices

- Mock `_get` and `_post` on `JiraClient` — do not mock individual helper functions
- Use `pytest.fixture` with appropriate scope for shared setup
- Test both happy path and error/edge cases for every method
- Use `side_effect` to simulate API errors
- Never call real Jira APIs in unit tests
- Coverage must stay at or above **85%** — run `--cov-fail-under=85` locally before pushing

---

## 8. AI Agent Instructions

### Safe Modifications

- **Interface changes** (`work_mgmt_client_interface`): Any change to ABCs, enums, or dataclasses is a **breaking change** for all implementations. Add new optional fields to `IssueUpdate` with `None` defaults. Do not remove or rename existing abstract methods without updating all implementations.
- **Jira implementation changes** (`jira_client_impl`): Safe to change internal logic as long as the public interface is preserved and unit tests pass.
- **New endpoints** (`main.py`): Add routes following the existing pattern — `Depends(oauth2_scheme)`, explicit `HTTPException` for all error paths, JSON response dict.
- **New platform implementation**: Create a new workspace member under `components/`, implement all ABCs from `work_mgmt_client_interface`, register via the `get_client()` factory.

### What NOT to Break

- `get_client()` factory registration — this is how implementations are discovered
- `sanitize_input()` in JQL construction — removing this introduces JQL injection vulnerabilities
- `_text_to_adf()` on write, `_extract_adf_text()` on read — Jira Cloud requires ADF; bypassing breaks descriptions
- `_apply_status_transition()` — Jira does not support direct status field writes; transitions are mandatory
- The 85% test coverage threshold — CI will fail
- mypy strict compliance — CI will fail on type errors
- The `user_sessions` dict structure in `auth.py` — `main.py` and `auth.py` both depend on its shape

### Consistency Rules

- Always run `ruff format .` before finalizing any change
- Always run `mypy components/ --explicit-package-bases` to verify types
- Never add `# type: ignore` without a comment explaining why
- Match the existing Google-style docstring format for any new public API
- New exceptions must subclass existing base exceptions from the interface layer
- Add pytest markers to every new test function

### When to Refactor vs. When Not To

- **Refactor:** If adding a new platform integration requires duplicating logic from `jira_client_impl`, extract it to a shared utility module instead
- **Do not refactor:** `main.py` is excluded from lint and type checks intentionally — keep it simple
- **Do not extract:** One-off helper logic used in exactly one place. Inline code is better than a single-use abstraction

---

## 9. Common Pitfalls

### JQL Injection
Any user-supplied string passed to JQL queries **must** go through `sanitize_input()` in `jira_impl.py`. Forgetting this allows attackers to manipulate Jira queries.

### ADF Format
Jira Cloud descriptions use Atlassian Document Format (ADF), not plain text. Always:
- Call `_text_to_adf(text)` before writing a description to Jira
- Call `_extract_adf_text(adf_body)` before surfacing a description from Jira to callers

Bypassing either conversion produces garbled output or Jira API errors.

### Status Transitions
Jira does not allow directly setting the `status` field. You must:
1. Fetch available transitions via `GET /rest/api/3/issue/{id}/transitions`
2. Match the desired status to a transition ID via `_STATUS_TO_JIRA_TRANSITION`
3. POST to the transitions endpoint

Skipping any step silently fails or raises a `JiraError`.

### OAuth Token Expiry
Never access `user_sessions[user_id]["access_token"]` directly. Always call `get_valid_token(user_id)` which handles automatic refresh when the token is near expiry.

### uv Workspace Resolution
All inter-component dependencies are declared in each component's `pyproject.toml`. If you add a new component, register it in the root `pyproject.toml` under `[tool.uv.workspace]` and run `uv sync`.

### mypy Strict Mode
Common failures:
- Missing return types on functions
- Untyped `**kwargs` in subclass overrides
- Missing stubs for third-party packages (add `types-*` dev dependencies)
- Use of `Any` without explicit annotation

### Test Marker Requirements
Tests without the correct markers will be excluded from the wrong CI stage. A test without `@pytest.mark.circleci` won't run in the `circleci_test` job. A test requiring credentials must have `@pytest.mark.local_credentials` to be excluded from CI automatically.

---

## 10. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `JIRA_OAUTH_CLIENT_ID` | Yes | Jira OAuth2 app client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | Yes | Jira OAuth2 app client secret |
| `JIRA_OAUTH_REDIRECT_URI` | Yes | OAuth callback URL (must match Jira app settings) |
| `JIRA_BASE_URL` | CI only | Jira instance URL (for integration tests) |
| `JIRA_API_TOKEN` | CI only | API token (for integration tests) |
| `JIRA_USER_EMAIL` | CI only | User email (for integration tests) |
| `JIRA_PROJECT_KEY` | CI only | Project key (for integration tests) |

---

## 11. CI/CD Pipeline (CircleCI)

**Branches other than `main`:**
```
build → lint → unit_test → circleci_test → report_summary
```

**`main` branch only:**
```
build → lint → unit_test → circleci_test → integration_test → report_summary
```

- `unit_test` runs mypy and enforces 85% coverage
- `circleci_test` runs tests marked `not local_credentials`
- `integration_test` requires the `jira-client` CircleCI context (secrets)
- Generated artifacts: `coverage.xml`, `test-results/*/junit.xml`

---

## 12. Suggested Improvements

- **Session persistence:** `user_sessions` is in-memory and lost on server restart. Consider Redis for production deployments.
- **Pagination in `get_issues()`:** The `Iterator[Issue]` return type is designed for lazy pagination — fetch next pages on demand rather than all at once upfront.
- **Config validation at startup:** Use Pydantic `BaseSettings` to validate required env vars on startup instead of failing at first request.
- **Structured logging:** Replace ad-hoc `logging` calls with structured JSON logging for CI/production observability.
- **Retry logic:** Jira Cloud has rate limits — add backoff/retry to `_get` and `_post` in `JiraClient`.
- **Auth abstraction:** `auth.py` is Jira-specific. As new platforms are added, extract an `AuthProvider` interface analogous to `IssueTrackerClient`.
