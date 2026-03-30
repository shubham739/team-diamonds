"""Development and debugging script for team-diamonds.

This script is excluded from ruff checks and is used for local development and testing.
For the FastAPI server, run:
    uvicorn jira_service.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
from dotenv import load_dotenv

# Loading .env from inside .venv
venv_env_path = os.path.join(os.path.dirname(__file__), ".venv", ".env")
load_dotenv(venv_env_path)

from jira_client_impl import get_client


def main() -> None:
    """Development main: test Jira client connectivity."""
    print("Hello from team-diamonds!")
    client = get_client(interactive=True)

    print("\nFetching recent issues...")
    # Test the get_issues generator
    try:
        issues = client.get_issues(max_results=5)
        for issue in issues:
            print(f"- {issue}")
    except Exception as e:
        print(f"Error connecting to Jira: {e}")

    try:
        issue = client.get_issue("OPS-20")
        print(f"- {issue}")
    except Exception as e:
        print(f"Error connecting to Jira: {e}")


if __name__ == "__main__":
    main()