#This file is for development purposes only

import logging

from jira_client_impl import get_client


def main():
    print("Hello from team-diamonds!")
    client = get_client(interactive=True)

    print("\nFetching recent issues...")
    # Let's test the get_issues generator
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