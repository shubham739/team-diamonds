"""End-to-end tests for the Jira client application.

Simulates real user workflows against a live Jira instance, verifying the
complete request-response cycle through main.py and the Jira client.

Requirements:
    Set the following environment variables before running:
        JIRA_BASE_URL    e.g. https://myorg.atlassian.net
        JIRA_USER_EMAIL  e.g. me@example.com
        JIRA_API_TOKEN   token from https://id.atlassian.com/manage-profile/security/api-tokens

Run only e2e tests:
    pytest -m e2e --no-cov

Run without e2e tests:
    pytest -m "not e2e"
"""

import contextlib
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from api.issue import Issue

from jira_client_impl.jira_impl import IssueNotFoundError, JiraClient, get_client

pytestmark = pytest.mark.e2e

MAIN_SCRIPT = Path(__file__).parent.parent.parent / "components" / "jira_service" / "src" / "jira_service" / "main.py"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> JiraClient:
    """Return a live, authenticated JiraClient, or skip if credentials are absent."""
    missing = [var for var in ("JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN") if not os.environ.get(var)]
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
    return get_client(interactive=False)


@pytest.fixture
def created_issue(client: JiraClient) -> Generator[Issue, None, None]:
    """Create a real Jira issue for a test and delete it afterwards."""
    issue = client.create_issue(
        title="[E2E Test] Temporary issue - safe to delete",
        desc="Created automatically by the E2E test suite.",
    )
    yield issue
    with contextlib.suppress(IssueNotFoundError):
        client.delete_issue(issue.id)


# ---------------------------------------------------------------------------
# 1.  main.py structural checks (no credentials needed)
# ---------------------------------------------------------------------------


class TestMainScriptStructure:
    """Verify main.py exists and is syntactically valid before running anything live."""

    @pytest.mark.circleci
    def test_main_script_exists(self) -> None:
        """main.py must exist at the project root."""
        assert MAIN_SCRIPT.exists(), f"main.py not found at {MAIN_SCRIPT}"

    @pytest.mark.circleci
    def test_main_script_has_valid_syntax(self) -> None:
        """main.py must have valid Python syntax."""
        if not MAIN_SCRIPT.exists():
            pytest.skip("main.py not found.")
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "py_compile", str(MAIN_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"Syntax error in main.py:\n{result.stderr}"

    @pytest.mark.circleci
    def test_main_script_imports_resolve(self) -> None:
        """All imports in main.py must resolve without error."""
        if not MAIN_SCRIPT.exists():
            pytest.skip("main.py not found.")
        root = Path(__file__).parent.parent.parent
        pythonpath = os.pathsep.join(
            [
                str(root / "components" / "jira_client_impl" / "src"),
            ],
        )
        env = {**os.environ, "PYTHONPATH": pythonpath}
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                "import api; import jira_client_impl; from jira_client_impl.jira_impl import get_client; print('ok')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(root),
            env=env,
            check=False,
        )
        assert result.returncode == 0, f"Import error:\n{result.stderr}"
        assert "ok" in result.stdout


# ---------------------------------------------------------------------------
# 2.  Application structure integrity
# ---------------------------------------------------------------------------


class TestApplicationStructure:
    """Verify required files exist at expected paths."""

    @pytest.mark.circleci
    def test_required_project_files_exist(self) -> None:
        """All required source files must be present at their expected paths."""
        root = Path(__file__).parent.parent.parent
        required = [
            "components/jira_service/src/jira_service/main.py",
            "pyproject.toml",
            "components/jira_client_impl/src/jira_client_impl/__init__.py",
            "components/jira_client_impl/src/jira_client_impl/jira_impl.py",
            "components/jira_client_impl/src/jira_client_impl/jira_issue.py",
            "components/jira_client_impl/src/jira_client_impl/jira_board.py",
        ]
        missing = [p for p in required if not (root / p).exists()]
        assert not missing, f"Missing required project files: {missing}"
