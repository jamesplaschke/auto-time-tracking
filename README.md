# Auto Time Tracking

Automatically pulls your Google Calendar events, classifies them into billable client work or overhead, and posts time entries to Rocketlane — with smart phase detection and duplicate prevention.

## How it works

1. **Pull** — fetches your calendar events for a given day, classifies each one by attendee domain and title patterns, and writes a JSON file for review
2. **Review** — inspect the output JSON and add `user_override` to any events that need corrections
3. **Post** — reads the reviewed JSON and posts time entries to Rocketlane with the correct project, phase, and category

---

## Setup

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Google Calendar API credentials (see below)
- Rocketlane API key (see below)

### Install

```bash
git clone https://github.com/jamesplaschke/auto-time-tracking
cd auto-time-tracking
uv sync
```

---

### 1. Google Calendar credentials

You need a `credentials.json` file from Google Cloud to allow this tool to read your calendar.

1. Go to [Google Cloud Console](https://console.cloud.google.com) and **create a new project** (or select an existing one)
2. In the left sidebar, go to **APIs & Services → Library**
3. Search for **Google Calendar API** and click **Enable**
4. Go to **APIs & Services → OAuth consent screen**
   - Choose **Internal** if your Google account is a Workspace account (recommended), or **External** if personal
   - Fill in an app name (e.g. "Auto Time Tracking") and your email — the rest can be left blank
   - Click **Save and Continue** through the remaining screens
5. Go to **APIs & Services → Credentials**
   - Click **+ Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name it anything (e.g. "auto-time-tracking")
   - Click **Create**
6. Click the **download icon** next to your new credential to download the JSON file
7. Rename it to `credentials.json` and place it in the **project root** (same folder as `pyproject.toml`)

**First run:** A browser window will open asking you to authorize access to your Google Calendar. After approving, a `token.json` file is created automatically — you won't be prompted again unless the token expires.

> `credentials.json` and `token.json` are listed in `.gitignore` and will never be committed.

---

### 2. Rocketlane API key

1. In Rocketlane, go to **Settings → API**
2. Copy your API key
3. In the project root, copy the example env file and paste in your key:

```bash
cp .env.example .env
```

Then edit `.env`:

```
ROCKETLANE_API_KEY=your-key-here
```

> `.env` is listed in `.gitignore` and will never be committed.

---

## Usage

### In the terminal

**Pull your calendar for a day:**

```bash
uv run pull-my-time-for 2026-02-18
uv run pull-my-time-for          # defaults to today
uv run pull-my-time-for --week   # Mon–Fri of current week
```

Output is written to `output/YYYY-MM-DD.json`. Review it and add `user_override` to any events that need corrections before posting.

**Post time entries to Rocketlane:**

```bash
uv run post-my-time-for 2026-02-18
uv run post-my-time-for 2026-02-18 --dry-run   # preview without posting
uv run post-my-time-for 2026-02-18 -y          # skip confirmation prompt
uv run post-my-time-for --week -y              # post full week
```

Duplicate detection prevents double-posting — safe to run multiple times.

---

### In Claude Code or Cursor

You can use this tool conversationally inside Claude Code or Cursor by describing what you want in plain English. The AI reads the output JSON, applies overrides, and runs the commands for you.

**Example prompts:**

> "Pull my time for today and show me what was classified."

> "Post today's time to Rocketlane — skip the standup and mark the Philips session as Configuration."

> "Pull and post the full week, skipping anything that's overhead."

The tool works the same way under the hood — the AI just handles the pull → review → override → post loop for you instead of you editing JSON manually.

**To enable this in Claude Code**, add the following to your project's `CLAUDE.md` or just describe your workflow once at the start of a session:

```
I use auto-time-tracking. The commands are:
  uv run pull-my-time-for [date|--week]
  uv run post-my-time-for [date|--week] [--dry-run] [-y]
Output is in output/YYYY-MM-DD.json. I will describe any overrides I need and you apply them before posting.
```

---

## Classification rules

Events are classified automatically using these rules (in priority order):

| Rule | Result |
|------|--------|
| Declined / cancelled / all-day | Skip |
| "Hold:" prefix, OOO, PTO, focus time, personal activities | Skip |
| Title matches a support ticket pattern | Support Tickets project |
| Title matches "enterprise methodology/pod" | Enterprise Methodology Pod |
| Title matches "value engineering" | Overhead → Enabling Work |
| Attendee domain matches a known client | That client's project |
| Title matches a known client name | That client's project |
| Internal-only attendees | Overhead (phase matched by title) |
| No attendees, title matches overhead pattern | Overhead |
| Everything else | Low confidence — review in JSON |

### Billable vs investment

Events are **reportable** by default for client projects. Events with words like `internal`, `prep`, `review`, `planning`, or `strategy` in the title are classified as **investment** (non-reportable).

### Phase detection

Phases are resolved automatically:
- **Configured clients** (Philips, Vista, etc.) use title pattern matching defined in `config.py`
- **All other clients** — phases are fetched from the Rocketlane API and the best match is selected by title word overlap

---

## Overriding a classification

Edit the output JSON and add a `user_override` field to any event:

```json
{
  "event": { "title": "Some Meeting" },
  "confidence": "low",
  "project_hints": [
    { "project_id": 123456, "project_name": "Acme Corp - Implementation" }
  ],
  "user_override": {
    "project_id": 123456,
    "phase_id": 789012,
    "billable": true,
    "notes": "Custom note for time entry"
  }
}
```

Set `"skip": true` in `user_override` to exclude an event from posting.

For **unknown external attendees**, `project_hints` shows the top matching Rocketlane projects to make overrides easy.

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
        (re.compile(r"(prep|planning)", re.IGNORECASE), "Planning"),
        (re.compile(r"support", re.IGNORECASE), "Support"),
    ],
),
```

Phase IDs are resolved automatically from the Rocketlane API — no need to look them up manually.
