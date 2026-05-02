# Slack App Setup for Bot Commands

## Step 1: Get Your Slack Signing Secret

1. Go to https://api.slack.com/apps
2. Select your existing Slack app (the one you got the bot token from)
3. Go to **Settings** → **Basic Information**
4. Scroll down to **App Credentials**
5. Copy the **Signing Secret**
6. Add it to your `.venv/.env` file:
   ```
   SLACK_SIGNING_SECRET=your_signing_secret_here
   ```

## Step 2: Enable Event Subscriptions

1. In your Slack app settings, go to **Features** → **Event Subscriptions**
2. Turn on **Enable Events**
3. Set the **Request URL** to: `http://your-server:8000/slack/events`
   - For local testing, you'll need to use ngrok or similar to expose your local server
   - For production, use your actual server URL

## Step 3: Subscribe to Bot Events

In the **Subscribe to bot events** section, add these events:
- `app_mention` - When someone mentions your bot with @bot

## Step 4: Get Bot User ID (Optional)

1. Go to **Features** → **OAuth & Permissions**
2. Scroll down to **Bot User OAuth Token** 
3. The bot user ID is in the token (starts with `U` after `xoxb-`)
4. Or you can get it by calling the Slack API: `https://slack.com/api/auth.test`
5. Add it to `.venv/.env`:
   ```
   SLACK_BOT_USER_ID=U1234567890
   ```

## Step 5: Install/Reinstall App

1. Go to **Settings** → **Install App**
2. Click **Reinstall to Workspace** (to pick up the new event subscriptions)
3. Make sure the bot is invited to the channels where you want to use it

## Step 6: Test the Setup

1. Start the bot server:
   ```bash
   .venv/Scripts/python.exe components/chat_to_issues_integration/slack_bot_server.py
   ```

2. In a Slack channel where the bot is present, try:
   ```
   @your-bot help
   @your-bot list issues
   @your-bot create issue: Test issue from Slack
   @your-bot post issues
   ```

## Local Development with ngrok

For local testing, you'll need to expose your local server to the internet:

1. Install ngrok: https://ngrok.com/
2. Run your bot server: `python slack_bot_server.py`
3. In another terminal: `ngrok http 8000`
4. Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)
5. Update your Slack app's Request URL to: `https://abc123.ngrok.io/slack/events`

## Environment Variables Needed

Make sure your `.venv/.env` has:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_USER_ID=U1234567890  # Optional but recommended
JIRA_SERVICE_BASE_URL=https://your-jira-service-url
JIRA_SERVICE_ACCESS_TOKEN=your-jira-token
```