# Auto Time Tracking

Automatically pulls your Google Calendar events, classifies them into billable client work or overhead, and posts time entries to Rocketlane — with smart phase detection and duplicate prevention.

## How it works

1. **Pull** — fetches your calendar events for a given day, classifies each one by attendee domain and title patterns, and writes a JSON file for review
2. **Review** — inspect the Slack summary (or output JSON) and reply with corrections in plain English
3. **Post** — click "Post to Rocketlane" in Slack, or run the CLI command

---

## New User Setup

### Prerequisites
- macOS or Linux
- [uv](https://docs.astral.sh/uv/) package manager (`brew install uv` on Mac)

### Step 1: Clone the repo

```bash
git clone https://github.com/jamesplaschke/auto-time-tracking
cd auto-time-tracking
uv sync
```

### Step 2: Get shared credentials from James

Ask James (Slack DM or 1Password) for these four items:

| Item | What it is |
|------|-----------|
| `credentials.json` | Google Calendar OAuth app config — drop this file in the repo root (same folder as `pyproject.toml`) |
| `SLACK_BOT_TOKEN` | Shared Slack bot token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Shared Slack app token for Socket Mode (`xapp-...`) |
| `ANTHROPIC_API_KEY` | Shared Claude API key for thread corrections (`sk-ant-...`) |

### Step 3: Generate your Rocketlane API key

1. Log in to [Rocketlane](https://app.rocketlane.com)
2. Go to **Settings → API**
3. Copy your personal API key

### Step 4: Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```bash
# Replace YOUR_NAME with your user ID (e.g., JAMES, KEVIN)
ROCKETLANE_API_KEY_YOUR_NAME=rl-your-key-here

# Paste the shared tokens James sent you
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ANTHROPIC_API_KEY=sk-ant-...
```

> `.env` is gitignored and will never be committed.

### Step 5: Authenticate Google Calendar

Run this once — a browser window will open asking you to sign in with your Google account:

```bash
uv run pull-my-time-for --user yourname
```

After approving, your OAuth token is saved to `tokens/yourname.json` (gitignored) and you won't be prompted again.

### You're done!

---

## Usage

### Pull (classify your calendar)

```bash
uv run pull-my-time-for                        # today, default user
uv run pull-my-time-for 2026-03-02             # specific date
uv run pull-my-time-for --week                 # Mon–Fri of current week
uv run pull-my-time-for --user kevin           # specific user
uv run pull-my-time-for --user all             # all registered users
uv run pull-my-time-for --week --user kevin    # combine flags
```

Output is written to `output/{user}/{date}.json`. A Slack DM is sent with the summary.

### Post (send to Rocketlane)

```bash
uv run post-my-time-for 2026-03-02                    # post a day
uv run post-my-time-for 2026-03-02 --dry-run           # preview without posting
uv run post-my-time-for 2026-03-02 -y                  # skip confirmation
uv run post-my-time-for --week -y --user kevin          # post full week for kevin
```

Duplicate detection prevents double-posting — safe to run multiple times.

### Via Slack

After pulling, you'll get a Slack DM with a summary table. From there:
- **Reply in the thread** with corrections in plain English (e.g., "skip the standup" or "move the Philips meeting to Configuration phase")
- **Click "Post to Rocketlane"** to post all entries

### In Claude Code

Use the slash commands:
- `/pull-timesheet [date] [--week] [--user USER]`
- `/post-timesheet [date] [--week] [--dry-run] [--user USER]`

Or just describe what you want in plain English:
> "Pull my time for today and post it"
> "Pull Kevin's time for the week"

---

## Classification rules

Events are classified automatically using these rules (in priority order):

| Rule | Result |
|------|--------|
| Declined / cancelled / all-day | Skip |
| "Hold:" prefix, OOO, PTO, focus time | Skip |
| Personal skip patterns (per-user) | Skip |
| Title matches a support ticket pattern | Support Tickets project |
| Title matches "enterprise methodology/pod" | Enterprise Methodology Pod |
| Title matches "value engineering" | Overhead → Enabling Work |
| Attendee domain matches a known client | That client's project |
| Title matches a known client name | That client's project |
| Internal-only attendees | Overhead (phase matched by title) |
| No attendees, title matches overhead pattern | Overhead |
| Everything else | Low confidence — review in Slack or JSON |

### Billable vs investment

Events are **reportable** by default for client projects. Events with words like `internal`, `prep`, `review`, `planning`, or `strategy` in the title are classified as **investment** (non-reportable).

### Phase detection

Phases are resolved automatically:
- **Configured clients** (Philips, Vista, etc.) use title pattern matching defined in `config.py`
- **All other clients** — phases are fetched from the Rocketlane API and the best match is selected by title word overlap

---

## Overriding a classification

Reply to the Slack DM thread with a correction in plain English:

> "Skip the standup"
> "Move the Philips session to Admin/Onboarding"
> "Mark the Acme meeting as billable reportable"

The AI interprets your instruction, updates the JSON, and auto-posts to Rocketlane.

You can also edit the output JSON directly and add a `user_override` field:

```json
{
  "user_override": {
    "project_id": 123456,
    "phase_id": 789012,
    "billable": true,
    "notes": "Custom note"
  }
}
```

Set `"skip": true` in `user_override` to exclude an event.

---

## Adding a new client

Add an entry to `CLIENT_PROJECTS` in `src/time_tracking/config.py`:

```python
ClientProject(
    name="Acme Corp",
    project_id=123456,
    domains=["acme.com"],
    default_phase_name="Implementation",
    phase_patterns=[
        (re.compile(r"(prep|planning)", re.IGNORECASE), "Planning"),
        (re.compile(r"support", re.IGNORECASE), "Support"),
    ],
),
```

Phase IDs are resolved automatically from the Rocketlane API — no need to look them up manually.

---

## Architecture

```
Google Calendar  →  pull-my-time-for (classify)
                      → output/{user}/{date}.json
                      → Slack DM with summary

Slack thread     →  slack_listener (corrections via Claude)
                      → update JSON + auto-post

Slack button     →  slack_listener → post_time_entries
                      → Rocketlane API

CLI post         →  post-my-time-for
                      → Rocketlane API
```

### Key files

| File | Purpose |
|------|---------|
| `src/time_tracking/users.py` | User registry — add new users here |
| `src/time_tracking/config.py` | Shared classification rules, client projects, patterns |
| `src/time_tracking/classifier.py` | Rule-based classification engine |
| `src/time_tracking/gcal_client.py` | Google Calendar API client |
| `src/time_tracking/rocketlane_client.py` | Rocketlane API client |
| `src/time_tracking/slack_listener.py` | Socket Mode daemon for Slack interactions |
