# Team Diamonds — A Component-Based Jira Client

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/shubham739/team-diamonds/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/shubham739/team-diamonds/tree/main)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Team Members

| NetID | Name | GitHub |
|-------|------|--------|
| — | Subhradeep Acharjee | — |
| — | Ethan Bell | @ethancharles13 |
| — | Shubham Tanwar | @shubham739 |
| — | Tanya Thomas | @tatyanacthomas |
| — | Conor Zhang | @cnrzhang |

---

## Architectural Philosophy

This project is built on the principle of **location transparency** — the idea that business logic should not care whether its dependencies are local libraries or remote services. The architecture is designed to be modular, testable, and evolvable.

- **Component-Based Design:** The system is broken into five distinct, self-contained components. Each has a single responsibility and can be reused or swapped independently.
- **Interface-Implementation Separation:** Every piece of functionality is defined by an abstract contract (ABC — the "what") and fulfilled by a concrete implementation (the "how"). This decouples consumers from specific technologies like Jira.
- **Dependency Injection:** Implementations are registered behind a stable `get_client()` factory. Consumers only ever depend on the abstract interface, not the volatile implementation details.
- **Adapter Pattern for Location Transparency:** The same interface contract is implemented twice — once as a direct library (Layers 1–2) and once as a thin adapter over an HTTP service (Layers 4–5). Switching between local and remote access requires changing only a single import.

---

## Core Components

The project is a `uv` workspace containing five packages arranged in a layered architecture:

| Layer | Package | Purpose |
|-------|---------|---------|
| 1 | `api` | External contract package — defines the shared client and domain models consumed by all components |
| 2 | `jira-client-impl` | Local Jira implementation — calls the Jira REST API directly using Basic Auth or OAuth2 |
| 3 | `jira-service` | FastAPI microservice — exposes layer 2 operations over HTTP with OAuth2 support |
| 4 | `jira-service-api-client` | Type-safe `httpx`-based HTTP client for the FastAPI service |
| 5 | `jira-service-adapter` | Adapter — wraps layer 4 behind the layer 1 interface, enabling remote access via the same `get_client()` call |

Consumers use the same call regardless of which path they choose:

```python
# Option A — direct library (local)
from jira_client_impl import get_client

# Option B — remote service
from jira_service_adapter import get_client

client = get_client()   # same interface, same call sites
```

---

## Project Structure

```
team-diamonds/
├── .circleci/
│   └── config.yml                             # CI pipeline: lint → test → coverage → deploy
│
├── .github/
│   └── (GitHub configuration)
│
├── components/
│   ├── (Contract layer provided by external `api` package dependency)
│   │
│   ├── jira_client_impl/                      # Layer 2: Direct Jira REST API implementation
│   │   ├── src/jira_client_impl/
│   │   │   ├── jira_impl.py                   # JiraClient — concrete implementation of the api client contract
│   │   │   ├── jira_issue.py                  # JiraIssue — parses Jira API responses
│   │   │   └── jira_board.py                  # JiraBoard — board/project operations
│   │   ├── pyproject.toml
│   │   └── tests/
│   │       └── test_core_methods.py
│   │
│   ├── jira_service/                          # Layer 3: FastAPI microservice
│   │   ├── src/jira_service/
│   │   │   ├── main.py                        # FastAPI app — REST endpoints for all CRUD operations
│   │   │   ├── auth.py                        # OAuth2 flow and session management
│   │   │   ├── exceptions.py
│   │   │   └── handler.py                     # AWS Lambda entry point (Mangum adapter)
│   │   ├── pyproject.toml
│   │   └── tests/
│   │       ├── test_auth.py
│   │       ├── test_handler.py
│   │       └── integration/test_api.py
│   │
│   ├── jira_service_api_client/               # Layer 4: Type-safe HTTP client for the service
│   │   ├── src/jira_service_api_client/
│   │   │   ├── client.py                      # JiraServiceClient — httpx-based HTTP client
│   │   │   └── models.py                      # IssueData, Status, HealthResponse dataclasses
│   │   ├── pyproject.toml
│   │   └── tests/
│   │       └── test_client.py
│   │
│   └── jira_service_adapter/                  # Layer 5: Adapter implementing interface via service
│       ├── src/jira_service_adapter/
│       │   ├── adapter.py                     # JiraServiceAdapter — wraps HTTP client behind ABC
│       │   └── issue.py                       # ServiceIssue — concrete Issue from HTTP response
│       ├── pyproject.toml
│       └── tests/
│           └── test_adapter.py
│
├── tests/
│   ├── integration/                           # Integration tests (live Jira API, CI-gated)
│   │   └── test_client_integration.py
│   └── e2e/                                   # End-to-end workflow tests
│       └── test_client_e2e.py
│
├── docs/                                      # MkDocs documentation site
│   ├── DESIGN.md
│   ├── INTERFACE.md
│   ├── CONTRIBUTING.md
│   ├── JIRA_SERVICE.md
│   ├── JIRA_SERVICE_API_CLIENT.md
│   ├── JIRA_SERVICE_ADAPTER.md
│   └── IMPLEMENTATION_JIRA.md
│
├── Dockerfile                                 # Docker image for Lambda/service deployment
├── mkdocs.yml                                 # MkDocs configuration
├── pyproject.toml                             # Shared tooling config (ruff, mypy, pytest, coverage)
├── uv.lock                                    # Locked dependency versions
└── LICENSE
```

---

## App URL
https://yx6edoh8l4.execute-api.us-east-2.amazonaws.com/default-deployment/docs

## Project Setup

### 1. Prerequisites

- Python **3.12** or higher
- [uv](https://docs.astral.sh/uv/) — a fast, all-in-one Python package manager

### 2. Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 3. Clone the Repository

```bash
git clone https://github.com/shubham739/team-diamonds.git
cd team-diamonds
```

### 4. Set Up Jira Credentials

**Option A — Basic Auth (local development)**

Generate an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens), then export:

```bash
export JIRA_BASE_URL="https://yourorg.atlassian.net"
export JIRA_USER_EMAIL="you@example.com"
export JIRA_API_TOKEN="your_api_token"
```

Or create a `.env` file in the project root:

```
JIRA_BASE_URL=https://yourorg.atlassian.net
JIRA_USER_EMAIL=you@example.com
JIRA_API_TOKEN=your_api_token
```

Then load it:

```bash
set -a && source .env && set +a
```

**Option B — OAuth2 (production multi-user)**

Register an OAuth2 app in the [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/) and export:

```bash
export JIRA_CLOUD_ID="your_cloud_id"
export JIRA_OAUTH_CLIENT_ID="your_client_id"
export JIRA_OAUTH_CLIENT_SECRET="your_client_secret"
export JIRA_OAUTH_REDIRECT_URI="http://localhost:8000/auth/callback"
```

Register **both** redirect URIs in your Atlassian OAuth app:

- **Local:** `http://localhost:8000/auth/callback`
- **Production:** `https://team-diamonds.onrender.com/auth/callback`

**CI/CD:** Configure `JIRA_API_TOKEN`, `JIRA_USER_EMAIL`, and `JIRA_BASE_URL` in CircleCI project settings under the `jira-client` context.

> **Important:** `.env` files may contain secrets and are ignored by `.gitignore`. Never commit credentials.

### 5. Create and Sync the Virtual Environment

This command creates a `.venv` folder and installs all packages (including workspace members and development tools) defined in `uv.lock`.

```bash
uv sync --all-packages --extra dev
```

### 6. Activate the Virtual Environment

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

---

## Development Workflow

All commands should be run from the project root with the virtual environment activated.

### Linting & Formatting (Ruff)

The project uses Ruff with comprehensive rules configured in `pyproject.toml` (line length 130).

```bash
# Check for issues
uv run ruff check .

# Automatically fix issues
uv run ruff check . --fix

# Check formatting
uv run ruff format --check .

# Apply formatting
uv run ruff format .
```

### Static Type Checking (MyPy)

```bash
uv run mypy .
```

MyPy runs in strict mode. All components are fully typed.

### Testing (Pytest)

The project uses a comprehensive testing strategy with an **85% coverage threshold**.

```bash
# Run all component unit tests (fast, no external dependencies)
uv run pytest components/

# Run all tests except those requiring local credential files
uv run pytest components/ tests/ -m "not local_credentials"

# Run only integration tests (requires Jira environment variables)
uv run pytest -m integration

# Run only end-to-end tests
uv run pytest -m e2e

# Run tests with coverage reporting
uv run pytest components/ --cov=components --cov-report=term-missing
```

### Running the Service Locally

```bash
uvicorn components.jira_service.src.jira_service.main:app --reload
```

The service starts on `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### Viewing Documentation

This project uses MkDocs for documentation.

```bash
# Start the live-reloading documentation server
uv run mkdocs serve
```

Open your browser to `http://127.0.0.1:8000` to view the site.

---

## Testing Infrastructure

The project implements a layered testing strategy designed for both local development and CI/CD environments.

### Test Categories

| Category | Location | Description |
|----------|----------|-------------|
| Unit | `components/*/tests/` | Fast, isolated tests with mocked dependencies |
| Integration | `tests/integration/` | Tests against the live Jira API (CI-gated) |
| End-to-End | `tests/e2e/` | Full application workflow tests |

### Test Markers

```python
@pytest.mark.unit               # Fast unit tests
@pytest.mark.integration        # Live Jira API tests
@pytest.mark.e2e                # End-to-end workflow tests
@pytest.mark.circleci           # Runs in CI without local credentials
@pytest.mark.local_credentials  # Requires local .env or credential files (skipped in CI)
```

### Authentication in Tests

The testing infrastructure handles different credential scenarios:

- **Local Development:** Requires `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, and `JIRA_API_TOKEN` set via environment variables or a `.env` file.
- **CI/CD Environment:** Set environment variables in CircleCI project settings under the `jira-client` context.
- **Missing Credentials:** Tests marked `local_credentials` are skipped automatically in CI; integration tests fail fast with a clear error message.

---

## Continuous Integration

The project includes a comprehensive CircleCI configuration (`.circleci/config.yml`) with two workflows:

**Feature branches** (`build_and_test`):
```
build → lint → unit_test → circleci_test → report_summary
```

**Main / release branches** (`full_integration`):
```
build → lint → unit_test → circleci_test → integration_test → report_summary → deploy
```

| Job | Description |
|-----|-------------|
| `build` | Installs uv and syncs all workspace dependencies |
| `lint` | Runs `ruff check .` |
| `unit_test` | Runs component tests, enforces 85% coverage, runs mypy |
| `circleci_test` | Runs all tests not requiring local credential files |
| `integration_test` | Runs live Jira API tests using the `jira-client` CircleCI context |
| `deploy` | Packages and deploys the Lambda zip to AWS Lambda (`us-east-2`) |
| `report_summary` | Aggregates test results and coverage artifacts |

---

## Quick Start

```bash
# 1. Install dependencies
uv sync --all-packages --extra dev

# 2. Run unit tests
uv run pytest components/ -v

# 3. Run all tests (excluding local credentials)
uv run pytest components/ tests/ -m "not local_credentials" -v

# 4. Check code quality
uv run ruff check . && uv run ruff format --check .

# 5. Fix formatting
uv run ruff format .

# 6. Type check
uv run mypy .

# 7. Start the service
uvicorn components.jira_service.src.jira_service.main:app --reload

# 8. View documentation
uv run mkdocs serve
```

**Best practices:**
- Run `uv run pytest components/` during development for fast feedback
- Use `-m integration` to verify live Jira connectivity before pushing
- Run the full test suite (`uv run pytest`) before opening a PR to ensure CI compatibility
- The CircleCI pipeline provides automated validation on every push

---

## Further Reading

- [Design & Architecture](docs/DESIGN.md)
- [Interface Contract](docs/INTERFACE.md)
- [Jira Service](docs/JIRA_SERVICE.md)
- [Jira Service API Client](docs/JIRA_SERVICE_API_CLIENT.md)
- [Jira Service Adapter](docs/JIRA_SERVICE_ADAPTER.md)
- [Jira Implementation](docs/IMPLEMENTATION_JIRA.md)
- [Contributing Guide](docs/CONTRIBUTING.md)
