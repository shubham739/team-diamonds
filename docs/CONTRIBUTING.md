# Contributing to Team Diamonds 

This document outlines the process for contributing to this open source library.

---
## Getting Started / Setup

### Prerequisites

- [Python >= 3.11]
- [uv](https://docs.astral.sh/uv/) — used to manage the virtual environment and dependencies

### Fork & Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/shubham739/team-diamonds.git
cd team-diamonds
```

### Install Dependencies

```bash
# Create the virtual environment and install all dependencies
uv sync --extra dev
```
`--extra dev` flag gives developers access to all necessary dependencies. 
Then:
```
pytest
ruff check .
mypy components/
```
The above set up ensures contributors can fully develop and validate changes locally. No special access is needed beyond cloning the repo, as `uv` and the pyproject.toml will handle dependency resolution.

### Running Locally

```bash
# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Project Structure Overview

Interface contracts are provided by the external `ospd-issue-tracker-api` package. Only production components are listed below; deprecated components (`jira_service_adapter`, `jira_service_api_client`, `work_mgmt_client_interface`, `jira_chat_bridge`, `chat_to_issues_integration`) remain in the repo but are not part of the live deployment.

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
│   ├── CONTRIBUTING.md
│   ├── CROSS_VERTICAL_INTEGRATION.md
│   ├── DEPLOYMENT_OVERVIEW.md
│   ├── DESIGN.md
│   ├── JIRA_CLIENT_IMPLEMENTATION.md
│   ├── JIRA_SERVICE.md
│   └── README.md
│
├── frontend/                                 # React frontend (served via CloudFront)
├── .circleci/config.yml                      # CI/CD pipeline
├── Dockerfile                                # Production Docker image
├── LICENSE                                   # Project license
├── mkdocs.yml                                # MkDocs configuration
├── pyproject.toml                            # Root uv workspace + ruff / mypy / pytest config
└── README.md
```

---

## Pull Request Process

### Branch Naming

Use descriptive branch names following the pattern:

```
[netid]-[hw#]-[feature_name]

```

Examples: `tct297-hw1-implementation_update`

### Workflow

1. Create a branch from `main` (or the designated development branch).
2. Following the test driven development method, write tests to cover your changes first
2. Then make your changes, and only commit atomic and reasonable changes
4. Run the full test suite locally and confirm it passes.
5. Update relevant documentation if behavior or APIs have changed.
6. Open a pull request against `main` and fill out the PR template.

### PR Template and Checklist

Use the following template when opening a pull request:

## Description
Please include a summary of the change and which issue is fixed, or which feature is implemented.

## Type of change
- [ ] Bug fix 
- [ ] New feature 

## Checklist:
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have tagged the appropriate reviewers
- [ ] I ran shell command `ruff check . --fix` and verified that there are no formatting errors
- [ ] I ran shell command `uv run mypy components/ --explicit-package-bases` and verified that there are no formatting errors
- [ ] I verified that all unit tests pass.
- [ ] If I added any dependencies, I updated the pyproject.toml files accordingly

### Review Process

- A reviewer will review your PR upon request
- Address review feedback by pushing additional commits
- Once approved, the reviewer will merge your PR

### Commit Message Convention

Ensure your commit is short but descriptive. 

#### Examples:
handle empty string input in [method-name]
add [feature name] to impl component

---

## Testing Guidelines

### Running Tests

```bash
# Run the full test suite
uv run pytest

# Run a specific test file
uv run pytest tests/[test_file.py]
```

### Test Coverage

```bash
# Generate a coverage report
[pending instructions]
```

Aim to maintain **[85%]** or greater test coverage. PRs that significantly reduce coverage will be asked to add additional tests before merging.

### Writing Tests

This project follows test driven development: a test must be written before any new code is written. The typical cycle is:

1. Write a failing test that defines the expected behavior.
2. Write the minimum code necessary to make the test pass.
3. Refactor as needed, keeping the tests green.

Additional conventions:

- Place integration and end-to-end tests in the `tests/` directory of the root folder. 
- Place unit tests in the component's `tests/` 
- Name test files `test_[module_name].py` to follow pytest conventions.

# FastAPI Service

## Setup
```bash
uv sync --extra dev #installs all dependancies
make setup
#if the app is not running
uv add "uvicorn[standard]" --reinstall
uvicorn main:app --reload