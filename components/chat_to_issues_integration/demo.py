"""Demo script showing the chat-to-issues integration in action.

This demonstrates:
1. Creating an IntegrationApp with a mock chat client and Jira adapter
2. Posting issues to a chat channel
3. Creating issues from chat messages

Run from repo root with:
    python -m chat_to_issues_integration.demo

Or from the component directory:
    cd components/chat_to_issues_integration
    python -m demo
"""

from unittest.mock import MagicMock

from chat_to_issues_integration import IntegrationApp, MockChatClient


def main() -> None:
    """Run the integration demo."""
    print("=== Chat-to-Issues Integration Demo ===\n")

    # 1. Set up the chat client (mock for now)
    print("1. Setting up MockChatClient for user 'alice'...")
    chat = MockChatClient(user_id="alice")
    general = chat.add_channel("general")
    requests = chat.add_channel("feature-requests")
    print(f"   Created channels: {[ch.name for ch in chat.get_channels()]}\n")

    # 2. Set up the tracker client (would use real credentials in production)
    print("2. Setting up tracker client...")
    print("   (In production, this would be JiraServiceAdapter with real credentials)")
    print("   (For this demo, we'll use a mock tracker)\n")

    # Mock tracker for demo purposes
    tracker = MagicMock()

    # Create some fake issues
    issue1 = MagicMock()
    issue1.id = "PROJ-1"
    issue1.title = "Fix login bug"
    issue1.status = "to_do"
    issue1.due_date = "2026-05-01"

    issue2 = MagicMock()
    issue2.id = "PROJ-2"
    issue2.title = "Add dark mode"
    issue2.status = "in_progress"
    issue2.due_date = None

    tracker.get_issues.return_value = [issue1, issue2]
    tracker.get_issue.return_value = issue1
    tracker.create_issue.return_value = issue1

    # 3. Wire them together
    print("3. Creating IntegrationApp...")
    app = IntegrationApp(tracker_client=tracker, chat_client=chat)
    print("   ✓ App initialized with tracker + chat clients\n")

    # 4. Demo: Post issues to chat
    print("4. Posting issues to #general channel...")
    posted = app.post_issues_to_channel(general.id, max_results=2)
    print(f"   Posted {len(posted)} messages:")
    for msg in posted:
        print(f"     - {msg.text}")
    print()

    # 5. Demo: Create issue from chat message
    print("5. Creating an issue from a chat message...")
    msg = chat.send_message(requests.id, "Please add export to CSV feature")
    print(f"   Message in #{requests.name}: '{msg.text}'")

    created_issue = app.create_issue_from_message(msg.id)
    print(f"   ✓ Created issue: {created_issue.id} - {created_issue.title}\n")

    # 6. Show isolation
    print("6. Demonstrating user isolation...")
    bob_chat = MockChatClient(user_id="bob")
    print(f"   Alice has {len(chat.get_channels())} channels")
    print(f"   Bob has {len(bob_chat.get_channels())} channels")
    print("   ✓ Each user has their own isolated state\n")

    print("=== Demo Complete ===")
    print("\nNext steps:")
    print("  - Replace MockChatClient with SlackChatClient for real Slack integration")
    print("  - Use real JiraServiceAdapter with deployed service credentials")
    print("  - Deploy as a FastAPI service with per-user dependency injection")


if __name__ == "__main__":
    main()
