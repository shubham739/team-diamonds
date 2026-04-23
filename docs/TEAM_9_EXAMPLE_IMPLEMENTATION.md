# Team 9 Example Implementation

## What Team 9 Builds (30 minutes of work)

### 1. Implement ChatClient for Their Slack
```python
# team9_slack_client.py
from chat_to_issues_integration.chat_client import ChatClient, Channel, Message
from slack_sdk import WebClient

class Team9SlackClient(ChatClient):
    def __init__(self, token: str):
        self._client = WebClient(token=token)
    
    def get_channels(self) -> list[Channel]:
        response = self._client.conversations_list()
        return [Channel(id=ch["id"], name=ch["name"]) 
                for ch in response["channels"]]
    
    def send_message(self, channel_id: str, text: str) -> Message:
        response = self._client.chat_postMessage(channel=channel_id, text=text)
        return Message(id=response["ts"], channel_id=channel_id, 
                      text=text, sender=None)
    
    # ... 3 more simple methods (we provide examples)
```

### 2. Use Team 1's Integration (5 minutes)
```python
# team9_bot.py
from chat_to_issues_integration import IntegrationApp
from jira_service_adapter.adapter import get_client as get_jira_client
from team9_slack_client import Team9SlackClient

# Connect to Team 1's Jira service
jira_client = get_jira_client()  # Uses Team 1's API
slack_client = Team9SlackClient(token=TEAM9_SLACK_TOKEN)

# Create integration (Team 1's component)
app = IntegrationApp(tracker_client=jira_client, chat_client=slack_client)

# Now Team 9 has full Slack ↔ Jira integration!
```

### 3. Team 9's Slack Bot Commands
```python
# Team 9's bot responds to:
@team9bot create issue: User can't login
@team9bot list issues
@team9bot post issues to #dev-team
@team9bot help
```

## What Team 9 Gets

### Immediate Capabilities
-  Create Jira issues from Slack messages
-  List Jira issues in Slack channels  
-  Post issue summaries to any Slack channel
-  Full CRUD operations on issues via Slack

### Advanced Workflows (Team 9 can build)
```python
# Auto-create issues from #bug-reports
@app.route("/slack/events")
def handle_message():
    if message.channel == "#bug-reports":
        issue = app.create_issue_from_message(message.id)
        app.post_issue_to_channel(issue.id, "#dev-notifications")

# Daily standup automation
@scheduler.scheduled_job('cron', hour=9)
def daily_standup():
    app.post_issues_to_channel("#standup", max_results=5)

# Sprint planning helper
def plan_sprint():
    todo_issues = app.get_issues(status=Status.TO_DO)
    for issue in todo_issues:
        app.post_issue_to_channel(issue.id, "#sprint-planning")
```

## Team 9's HW3 Submission

**What they demonstrate:**
1. **Cross-vertical integration** ✅
   - Team 9 (Chat) integrates with Team 1 (Issue Tracker)
   
2. **API consumption** ✅  
   - Uses Team 1's deployed Jira API service
   
3. **Working functionality** ✅
   - Live Slack bot with Jira integration
   
4. **Minimal code** ✅
   - Just ChatClient implementation (~50 lines)
   - Everything else provided by Team 1

**Their demo:**
```
# In their Slack workspace:
@team9bot create issue: Add dark mode feature
# → Creates issue in Team 1's Jira via Team 1's API

@team9bot list issues  
# → Shows issues from Team 1's Jira via Team 1's API

@team9bot post issues to #product-team
# → Posts issue summaries to their Slack channel
```

## Win-Win Collaboration

**Team 1 (You) Benefits:**
-  Another team uses your Jira API service
-  Demonstrates cross-vertical integration
-  Validates your integration component

**Team 9 Benefits:**  
-  Gets full Slack ↔ Jira integration with minimal work
-  Satisfies HW3 cross-vertical requirement
-  Real business value for their Slack features