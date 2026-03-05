# Setup Guide for Auto Time Tracking

No coding experience needed. You'll run one script and follow the prompts.

---

## Step 1: Get two files from James

James will send you over Slack or 1Password:

1. **`credentials.json`** — a file, save it anywhere for now (you'll be prompted where to put it)
2. **`setup.sh`** — the setup script, save it to your **Downloads** folder

Also grab 3 keys James will send you:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ANTHROPIC_API_KEY=sk-ant-...
```
Keep these handy — the script will ask for them.

---

## Step 2: Get your Rocketlane API key

1. Go to [app.rocketlane.com](https://app.rocketlane.com) and log in
2. Click **Settings** (gear icon, bottom left)
3. Click **API** in the sidebar
4. Copy your API key — you'll need it in the next step

---

## Step 3: Run setup

Open **Terminal** and paste:

```
bash ~/Downloads/setup.sh --user kevin
```

Replace `kevin` with your user ID (ask James if unsure).

The script will:
- Install everything it needs automatically
- Ask you to drop `credentials.json` into the right folder
- Ask for your 4 API keys (Rocketlane + the 3 from James) — input is hidden as you type
- Open a browser window to connect your Google Calendar — sign in with your @ketryx.com account
- Learn your patterns from the last 30 days of data
- Run your first time pull and send you a Slack DM

**That's it.** The whole thing takes about 5 minutes.

---

## Day-to-day usage

Once setup is done, run this each day:

```
cd ~/auto-time-tracking && uv run pull-my-time-for --user kevin
```

Or for a specific date:
```
uv run pull-my-time-for 2026-03-02 --user kevin
```

Or a full week (Monday to Friday):
```
uv run pull-my-time-for --week --user kevin
```

You'll get a Slack DM with the results. Reply in the thread to make corrections, then click "Post to Rocketlane" when it looks right.

---

## Troubleshooting

**"command not found: git"** — Run `xcode-select --install`, then re-run setup.sh.

**Google sign-in shows a warning** — Click "Advanced" → "Go to Auto Time Tracking (unsafe)". Normal for internal apps.

**"credentials.json still not found"** — Make sure you moved it to `~/auto-time-tracking/` (the script tells you the exact path).

**Made a mistake entering an API key** — Delete the `.env` file in `~/auto-time-tracking/` and re-run `bash ~/Downloads/setup.sh --user kevin`.

Still stuck? Message James on Slack.
