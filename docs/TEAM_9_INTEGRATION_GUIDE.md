# Integration Guide for Team 9 (Slack)

## Overview
Team 1 (Jira) provides a cross-vertical integration component that allows Team 9 (Slack) to integrate with our Jira API service. Team 9 gets full issue tracking capabilities through our service without needing to set up or manage their own Jira instance.

## What We Provide

### 1. Jira API Service (Already Deployed)
- **Endpoint**: `https://yx6edoh8l4.execute-api.us-east-2.amazonaws.com/default-deployment`
- **Authentication**: Bearer token (we'll provide)
- **API**: Implements `ospd-issue-tracker-api` standard

### 2. Integration Component
- **Package**: `chat_to_issues_integration`
- **Main Class**: `IntegrationApp`
- **Chat Interface**: `ChatClient` ABC (you implement for Slack)

## How Team 9 Can Use This

### Step 1: Implement ChatClient for Your Slack
```python
from chat_to_issues_integration.chat_client import ChatClient, Channel, Message
from slack_sdk import WebClient

class Team9SlackClient(ChatClient):
    def __init__(self, token: str):
        self._client = WebClient(token=token)
    
    def get_channels(self) -> list[Channel]:
        # Your Slack implementation
        pass
    
    def send_message(self, channel_id: str, text: str) -> Message:
        # Your Slack implementation
        pass
    
    # ... implement other methods
```

### Step 2: Use Our Integration
```python
from chat_to_issues_integration import IntegrationApp
from jira_service_adapter.adapter import get_client as get_jira_client

# Set up clients
jira_client = get_jira_client()  # Uses our API service
slack_client = Team9SlackClient(token=your_slack_token)

# Create integration
app = IntegrationApp(tracker_client=jira_client, chat_client=slack_client)

# Use integration
app.post_issues_to_channel(channel_id, max_results=5)
issue = app.create_issue_from_message(message_id)
```

### Step 3: Environment Variables
```bash
# Use our Jira API service
JIRA_SERVICE_BASE_URL=https://yx6edoh8l4.execute-api.us-east-2.amazonaws.com/default-deployment
JIRA_SERVICE_ACCESS_TOKEN=<we_provide_this>

# Your Slack credentials
SLACK_BOT_TOKEN=<your_slack_token>
```

## Benefits for Team 9
-  **No Jira setup required** - use our managed Jira service
-  **Ready-made integration logic** - just implement ChatClient
-  **Full issue tracking** - create, manage, track issues via Slack
-  **Cross-vertical integration** - Chat vertical using Issue Tracker vertical
-  **Satisfies HW3 requirements** for both teams

## Benefits for Team 1
-  **Our API service gets used** by another team
-  **True cross-vertical integration** - we provide issue tracking service
-  **Demonstrates our issue tracker API** value

## Contact
- Team 1 contact: [your contact info]
- Integration component: `components/chat_to_issues_integration/`
- Documentation: `components/chat_to_issues_integration/README.md`