# Examples

This directory contains example scripts demonstrating how to use the chat-to-issues integration component.

## Files

### `slack_demo_full.py`
Full demonstration of the Slack integration with Jira. Shows how to:
- Initialize the Slack client
- Create an IntegrationApp
- Post Jira issues to Slack channels
- Create Jira issues from Slack messages

**Usage:**
```bash
python components/chat_to_issues_integration/examples/slack_demo_full.py
```

**Prerequisites:**
- `SLACK_BOT_TOKEN` environment variable set
- `JIRA_SERVICE_BASE_URL` and `JIRA_SERVICE_ACCESS_TOKEN` configured
- Bot invited to Slack channels

## Running Examples

All examples should be run from the repository root:

```bash
# Set up environment variables
export SLACK_BOT_TOKEN="xoxb-your-token"
export JIRA_SERVICE_BASE_URL="https://your-jira-service.com"
export JIRA_SERVICE_ACCESS_TOKEN="your-token"

# Run the demo
python components/chat_to_issues_integration/examples/slack_demo_full.py
```

## See Also

- [Main README](../README.md) - Component overview and installation
- [Setup Guide](../setup_slack_app.md) - How to configure Slack app
- [Integration Summary](../../../docs/INTEGRATION_SUMMARY.md) - Architecture details
