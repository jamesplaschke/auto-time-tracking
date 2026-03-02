# Setup Guide for Auto Time Tracking

This walks you through getting the time tracking tool running on your Mac, step by step. No coding experience needed.

---

## Step 1: Install the `uv` package manager

Open **Terminal** (press Cmd+Space, type "Terminal", hit Enter) and paste this:

```
brew install uv
```

If you don't have Homebrew installed, run this first:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## Step 2: Download the code

In Terminal, paste these three commands one at a time:

```
git clone https://github.com/jamesplaschke/auto-time-tracking.git
```

```
cd auto-time-tracking
```

```
uv sync
```

This downloads the project into a folder called `auto-time-tracking` on your computer (inside your home directory), then installs everything it needs.

---

## Step 3: Add the files James sends you

James will send you two things over Slack or 1Password:

### 1. `credentials.json` (a file)

Save this file into the `auto-time-tracking` folder. That's the top-level folder you just downloaded — the one that contains `pyproject.toml`, `README.md`, etc.

To find it in Finder: open Finder, press Cmd+Shift+G, and paste:
```
~/auto-time-tracking
```

Drop `credentials.json` in there.

### 2. A message with four secret keys

James will send you something like:

```
SLACK_BOT_TOKEN=xoxb-1234-abcd...
SLACK_APP_TOKEN=xapp-5678-efgh...
ANTHROPIC_API_KEY=sk-ant-ijkl...
```

You'll use these in the next step.

---

## Step 4: Create your `.env` file

The `.env` file is a small text file that holds your secret keys (API passwords). The app reads this file when it runs. It stays on your computer and never gets uploaded.

In Terminal, make sure you're in the project folder:

```
cd ~/auto-time-tracking
```

Then create the file by copying the template:

```
cp .env.example .env
```

Now open it in TextEdit:

```
open -a TextEdit .env
```

You'll see placeholder text. Replace it so it looks like this (using the real keys James sent you and your own Rocketlane key):

```
ROCKETLANE_API_KEY_KEVIN=rl-paste-your-rocketlane-key-here

SLACK_BOT_TOKEN=xoxb-paste-the-real-token-here
SLACK_APP_TOKEN=xapp-paste-the-real-token-here
ANTHROPIC_API_KEY=sk-ant-paste-the-real-key-here
```

Delete any other lines you see (like the JAMES key or comment lines starting with `#`). Save and close.

### Where to get your Rocketlane API key

1. Go to [app.rocketlane.com](https://app.rocketlane.com) and log in
2. Click **Settings** (gear icon, bottom left)
3. Click **API** in the sidebar
4. Copy your API key

---

## Step 5: Run it for the first time

In Terminal:

```
cd ~/auto-time-tracking
uv run pull-my-time-for --user kevin
```

A browser window will open asking you to sign into Google. **Use your kevinb@ketryx.com account.** Click through the permissions — this lets the tool read your calendar.

After you approve, go back to Terminal. You should see your calendar events classified and a Slack DM with the summary.

---

## Day-to-day usage

Once setup is done, you just run this each day:

```
cd ~/auto-time-tracking
uv run pull-my-time-for --user kevin
```

Or for a specific date:

```
uv run pull-my-time-for 2026-03-02 --user kevin
```

Or a full week (Monday to Friday):

```
uv run pull-my-time-for --week --user kevin
```

You'll get a Slack DM with the results. Reply in the thread if anything needs correcting, then click "Post to Rocketlane" when it looks right.

---

## Troubleshooting

**"command not found: git"** — Install Xcode tools: `xcode-select --install`

**"command not found: brew"** — Install Homebrew (see Step 1)

**Google sign-in shows a warning** — Click "Advanced" → "Go to Auto Time Tracking (unsafe)". This is normal for internal apps.

**"No such file or directory: .env"** — Make sure you're in the right folder: `cd ~/auto-time-tracking`

Still stuck? Message James on Slack.
