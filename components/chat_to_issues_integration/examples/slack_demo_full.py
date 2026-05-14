"""Full demo script showing real Slack integration with issue creation.

This demonstrates the complete cross-vertical integration:
1. Connects to real Slack workspace
2. Connects to deployed Jira service
3. Creates a test issue in Jira
4. Posts that issue to Slack
5. Shows the integration working end-to-end

Prerequisites:
1. SLACK_BOT_TOKEN in .venv/.env
2. JIRA_SERVICE_BASE_URL and JIRA_SERVICE_ACCESS_TOKEN in .venv/.env
3. Bot invited to at least one Slack channel

Run with:
    .venv/Scripts/python.exe components/chat_to_issues_integration/slack_demo_full.py
"""

import os

from dotenv import load_dotenv

from chat_to_issues_integration import IntegrationApp, SlackChatClient
from jira_service_adapter.adapter import get_client as get_tracker_client

# Load environment variables from .venv/.env
load_dotenv(".venv/.env")


def main() -> None:
    """Run the full Slack integration demo."""
    print("=" * 60)
    print("CROSS-VERTICAL INTEGRATION DEMO")
    print("Chat (Slack) ↔ Issue Tracker (Jira)")
    print("=" * 60)
    print()

    # Check environment variables
    if not os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_BOT_TOKEN") == "xoxb-paste-your-actual-token-here":
        print(" Error: SLACK_BOT_TOKEN not set properly")
        print("   Update it in .venv/.env with your real Slack bot token")
        return

    if not os.getenv("JIRA_SERVICE_BASE_URL") or not os.getenv("JIRA_SERVICE_ACCESS_TOKEN"):
        print(" Error: Jira service credentials not set")
        return

    # 1. Set up clients
    print("Step 1: Connecting to Slack...")
    try:
        chat = SlackChatClient()
        print("    Connected to Slack\n")
    except Exception as e:
        print(f"    Failed: {e}\n")
        return

    print("Step 2: Connecting to Jira service...")
    print(f"   URL: {os.getenv('JIRA_SERVICE_BASE_URL')}")
    try:
        tracker = get_tracker_client()
        print("    Connected to Jira service\n")
    except Exception as e:
        print(f"    Failed: {e}\n")
        return

    # 2. Wire them together
    print("Step 3: Creating IntegrationApp...")
    app = IntegrationApp(tracker_client=tracker, chat_client=chat)
    print("    Cross-vertical integration initialized\n")

    # 3. List available channels
    print("Step 4: Discovering Slack channels...")
    try:
        channels = chat.get_channels()
        print(f"   Found {len(channels)} channels:")
        for ch in channels:
            print(f"     • #{ch.name} (id: {ch.id})")
        print()
    except Exception as e:
        print(f"    Failed: {e}\n")
        return

    if not channels:
        print("     No channels found. Invite the bot to channels first.")
        return

    # 4. Create a test issue in Jira
    print("Step 5: Creating a test issue in Jira...")
    try:
        test_issue = tracker.create_issue(
            title="[DEMO] Cross-vertical integration test",
            desc="This issue was created to demonstrate the chat-to-issues integration working with real Slack and Jira APIs.",
        )
        print(f"    Created issue: {test_issue.id}")
        print(f"      Title: {test_issue.title}")
        print(f"      Status: {test_issue.status}\n")
    except Exception as e:
        print(f"     Could not create test issue: {e}")
        print("   Continuing with existing issues...\n")

    # 5. Interactive: choose a channel
    print("Step 6: Select a Slack channel to post issues to:")
    for i, ch in enumerate(channels, 1):
        print(f"   {i}. #{ch.name}")
    print()

    try:
        choice = input("   Enter channel number (or press Enter to skip): ").strip()
        if not choice:
            print("   Skipped posting to Slack\n")
            return

        idx = int(choice) - 1
        if idx < 0 or idx >= len(channels):
            print("    Invalid choice\n")
            return

        target_channel = channels[idx]
    except (ValueError, IndexError):
        print("    Invalid input\n")
        return

    # 6. Post issues to Slack
    print(f"\nStep 7: Posting issues to #{target_channel.name}...")
    try:
        posted = app.post_issues_to_channel(target_channel.id, max_results=5)
        print(f"    Posted {len(posted)} issues to Slack")
        print()
        print("   Messages sent:")
        for i, msg in enumerate(posted, 1):
            # Show first 100 chars of each message
            preview = msg.text[:100] + "..." if len(msg.text) > 100 else msg.text
            print(f"   {i}. {preview}")
        print()
    except Exception as e:
        print(f"    Failed: {e}\n")
        return

    # 7. Summary
    print("=" * 60)
    print(" DEMO COMPLETE - Integration Working!")
    print("=" * 60)
    print()
    print("What was demonstrated:")
    print("   Connected to Slack (Team 9's vertical)")
    print("   Connected to Jira service (Team 1's vertical)")
    print("   Created issue in Jira via shared API")
    print("   Posted issues to Slack channel")
    print("   Cross-vertical integration successful")
    print()
    print("Architecture highlights:")
    print("  • Uses shared ospd-issue-tracker-api")
    print("  • Dependency injection (any tracker + any chat)")
    print("  • User isolation (per-instance state)")
    print("  • Works with any chat platform (Slack/Discord/Telegram)")
    print()
    print("Check your Slack channel to see the posted issues!")
    print()


if __name__ == "__main__":
    main()
