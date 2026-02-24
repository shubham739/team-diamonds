# from src.work_mgmt_client_interface.src.work_mgmt_client_interface.client import get_client
from src.jira_client_impl.src.jira_client_impl.jira_impl import get_client

def main():
    print("Hello from team-diamonds!")
    client = get_client(interactive=True)

    print("\nFetching recent issues...")
    # Let's test the get_issues generator
    try:
        issues = client.get_issues(max_results=5)
        for issue in issues:
            print(f"- {issue}") # Assuming your JiraIssue class has a __str__ or __repr__
    except Exception as e:
        print(f"Error connecting to Jira: {e}")

if __name__ == "__main__":
    main()
