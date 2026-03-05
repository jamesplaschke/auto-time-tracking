"""Training script: pre-populate correction memory from historical calendar + Rocketlane data."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "cache"


def _load_projects_cache() -> dict:
    cache_path = CACHE_DIR / "rocketlane_projects_phases.json"
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text())


def _resolve_project_name(project_id: int | None, cache: dict) -> str | None:
    if project_id is None:
        return None
    entry = cache.get(str(project_id))
    if not entry:
        return None
    return entry.get("name") if isinstance(entry, dict) else str(entry)


def _resolve_phase_name(project_id: int | None, phase_id: int | None, cache: dict) -> str | None:
    if project_id is None or phase_id is None:
        return None
    entry = cache.get(str(project_id))
    if not entry or not isinstance(entry, dict):
        return None
    for phase in entry.get("phases", []):
        if phase.get("phaseId") == phase_id:
            return phase.get("phaseName")
    return None


def _weekdays_in_range(days: int) -> list[date]:
    """Return the last N weekdays (Mon-Fri), starting from yesterday."""
    result = []
    d = date.today() - timedelta(days=1)
    while len(result) < days:
        if d.weekday() < 5:
            result.append(d)
        d -= timedelta(days=1)
    return result


def fetch_training_data(user, days: int = 30) -> list[dict]:
    """Fetch calendar + Rocketlane data for the last N weekdays."""
    from .classifier import classify_events
    from .gcal_client import fetch_events
    from .rocketlane_client import get_time_entries

    cache = _load_projects_cache()
    target_dates = _weekdays_in_range(days)
    training_data = []

    for target_date in target_dates:
        date_str = target_date.isoformat()

        try:
            events = fetch_events(target_date, user=user)
        except Exception as e:
            print(f"  Warning: could not fetch calendar for {date_str}: {e}")
            events = []

        try:
            rl_entries_raw = get_time_entries(date_str, api_key=user.rocketlane_api_key)
        except Exception as e:
            print(f"  Warning: could not fetch Rocketlane for {date_str}: {e}")
            rl_entries_raw = []

        classified = classify_events(events) if events else []

        cal_events = []
        for ev in events:
            delta = (ev.end - ev.start).total_seconds() / 60
            domains = list({
                att.email.split("@")[-1]
                for att in ev.attendees
                if "@" in att.email and not att.is_self
            })
            cal_events.append({
                "title": ev.title,
                "minutes": round(delta),
                "attendee_domains": domains,
            })

        rl_entries = []
        for entry in rl_entries_raw:
            project_id = (entry.get("project") or {}).get("projectId")
            phase_id = (entry.get("projectPhase") or {}).get("phaseId")
            rl_entries.append({
                "project_name": _resolve_project_name(project_id, cache) or f"project:{project_id}",
                "phase_name": _resolve_phase_name(project_id, phase_id, cache)
                    or (entry.get("projectPhase") or {}).get("phaseName"),
                "minutes": entry.get("minutes", 0),
            })

        classifier_output = []
        for c in classified:
            if c.skip:
                continue
            classifier_output.append({
                "title": c.event.title,
                "classified_project": c.project.project_name if c.project else None,
                "classified_phase": c.project.phase_name if c.project else None,
                "confidence": c.confidence.value,
            })

        training_data.append({
            "date": date_str,
            "calendar_events": cal_events,
            "rocketlane_entries": rl_entries,
            "classifier_output": classifier_output,
        })

    return training_data


def build_training_prompt(training_data: list[dict], user_id: str) -> str:
    data_json = json.dumps(training_data, indent=2)
    return f"""You are analyzing {len(training_data)} days of calendar events vs Rocketlane time entries for user "{user_id}".

For each day, you have:
- calendar_events: what was on their calendar (title, duration in minutes, attendee domains)
- rocketlane_entries: what was actually logged to Rocketlane that day
- classifier_output: what the auto-classifier predicted (title -> project/phase)

Here is the data:
{data_json}

Your task: identify recurring patterns where the classifier is wrong or events should be skipped.

Match calendar events to Rocketlane entries by:
1. Same date
2. Similar duration (within 15 minutes)
3. Logical project/phase match given the event title

Output a JSON array of correction rules. Only include patterns you see on MULTIPLE days (at least 2 occurrences). Skip one-off events.

For each pattern:
- If the classifier predicted a different project/phase than what Rocketlane shows -> action="reclassify"
- If the event appears on calendar but was never logged AND is clearly personal/non-work -> action="skip"

Use this exact schema (output ONLY the JSON array, no markdown fences, no explanation):
[
  {{
    "event_title": "short partial title to match (case-insensitive substring)",
    "action": "reclassify or skip",
    "project_id": <int or null>,
    "project_name": "<string or null>",
    "phase_name": "<string or null>",
    "billable": <true or false>,
    "billable_type": "<reportable or investment or null>"
  }}
]

Notes:
- event_title should be a short substring that uniquely identifies the recurring event type
- For reclassify: set project_id, project_name, phase_name, billable, billable_type to match Rocketlane
- For skip: set project_id=null, project_name=null, phase_name=null, billable=false, billable_type=null
- If no patterns are found, output an empty array: []
"""


def parse_corrections(response_text: str) -> list[dict]:
    """Parse Claude's JSON array response into correction dicts."""
    text = response_text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return []


def run_training(user, days: int = 30) -> None:
    """Orchestrate training: fetch data, call Claude, save corrections."""
    import anthropic
    from dotenv import load_dotenv

    from .correction_memory import upsert_memories

    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    print(f"Fetching {days} weekdays of calendar + Rocketlane data for {user.user_id}...")
    training_data = fetch_training_data(user, days=days)

    days_with_data = [d for d in training_data if d["calendar_events"] or d["rocketlane_entries"]]
    print(f"Found {len(days_with_data)} days with data (out of {len(training_data)} weekdays checked)")

    if not days_with_data:
        print("No data found. Nothing to learn from.")
        return

    print("Sending to Claude for pattern analysis...")
    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_training_prompt(days_with_data, user.user_id)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    corrections = parse_corrections(response_text)

    if not corrections:
        print("No recurring patterns found. Correction memory unchanged.")
        return

    upserted = upsert_memories(user.user_id, corrections, "training: auto-learned from historical data")

    print(f"\nDone! Saved {upserted} correction rules for {user.user_id}.")
    print("Patterns learned:")
    for c in corrections:
        action = c.get("action", "?")
        title = c.get("event_title", "?")
        project = c.get("project_name") or "(skip)"
        phase = c.get("phase_name") or ""
        phase_str = f" / {phase}" if phase else ""
        print(f"  [{action}] '{title}' -> {project}{phase_str}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-populate correction memory from historical Google Calendar + Rocketlane data."
    )
    parser.add_argument("--user", required=True, help="User ID (e.g. james, kevin)")
    parser.add_argument(
        "--days", type=int, default=30, help="Number of weekdays to analyze (default: 30)"
    )
    args = parser.parse_args()

    from .users import get_user

    user = get_user(args.user.lower())
    run_training(user, days=args.days)


if __name__ == "__main__":
    main()
