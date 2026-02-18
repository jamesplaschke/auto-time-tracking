# Auto Time Tracking

Automatically pulls your Google Calendar events, classifies them into billable client work or overhead, and posts time entries to Rocketlane — with smart phase detection and duplicate prevention.

## How it works

1. **Pull** — fetches your calendar events for a given day, classifies each one by attendee domain and title patterns, and writes a JSON file for review
2. **Review** — inspect the output JSON and add `user_override` to any events that need corrections
3. **Post** — reads the reviewed JSON and posts time entries to Rocketlane with the correct project, phase, and category

## Setup

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Google Calendar API credentials
- Rocketlane API key

### Install

```bash
git clone https://github.com/jamesplaschke/auto-time-tracking
cd auto-time-tracking
uv sync
```

### Google Calendar credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a project
2. Enable the **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Desktop app) and download as `credentials.json`
4. Place `credentials.json` in the project root
5. On first run, a browser window will open to authorize access — this creates `token.json`

### Rocketlane API key

Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
```

```
ROCKETLANE_API_KEY=rl-your-key-here
```

Find your key in Rocketlane under **Settings → API**.

---

## Usage

### Pull your calendar for a day

```bash
uv run pull-my-time-for 2026-02-18
uv run pull-my-time-for          # defaults to today
uv run pull-my-time-for --week   # Mon–Fri of current week
```

Output is written to `output/YYYY-MM-DD.json`. Review it and add `user_override` to any events that need corrections before posting.

### Post time entries to Rocketlane

```bash
uv run post-my-time-for 2026-02-18
uv run post-my-time-for 2026-02-18 --dry-run   # preview without posting
uv run post-my-time-for 2026-02-18 -y          # skip confirmation prompt
uv run post-my-time-for --week -y              # post full week
```

Duplicate detection prevents double-posting — safe to run multiple times.

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
        (re.compile(r"\b(prep|planning)\b", re.IGNORECASE), "Planning"),
        (re.compile(r"\bsupport\b", re.IGNORECASE), "Support"),
    ],
),
```

Phase IDs are resolved automatically from the Rocketlane API — no need to look them up manually.
