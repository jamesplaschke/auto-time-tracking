"""Script 1: Fetch Google Calendar events, classify them, write JSON output."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from .classifier import classify_events
from .config import TIMEZONE
from .display import console, print_day_summary
from .gcal_client import fetch_events
from .models import Confidence, DayClassification
from .overlap import resolve_overlaps
from .rocketlane_client import suggest_projects

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _get_week_dates(ref_date: date) -> list[date]:
    """Get Mon-Fri of the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def process_date(target_date: date) -> DayClassification:
    """Fetch, classify, and resolve events for a single date."""
    console.print(f"[dim]Fetching events for {target_date}...[/dim]")
    events = fetch_events(target_date)
    console.print(f"[dim]Found {len(events)} events.[/dim]")

    classified = classify_events(events)
    classified = resolve_overlaps(classified)

    # Attach project hints to unknown-external events
    unknown_events = [e for e in classified if e.category.startswith("unknown-external:")]
    if unknown_events:
        try:
            for event in unknown_events:
                domain = event.category.split("unknown-external:", 1)[1].split(",")[0].strip()
                event.project_hints = suggest_projects(domain, event.event.title)
        except Exception:
            pass  # hints are best-effort, don't fail the whole run

    tracked = [e for e in classified if not e.skip]
    total_tracked = sum(e.duration_minutes for e in tracked)
    total_billable = sum(e.duration_minutes for e in tracked if e.billable)
    total_non_billable = total_tracked - total_billable
    skipped_count = sum(1 for e in classified if e.skip)
    low_conf_count = sum(1 for e in tracked if e.confidence == Confidence.LOW)

    now = datetime.now(tz=ZoneInfo(TIMEZONE))

    return DayClassification(
        date=target_date.isoformat(),
        generated_at=now.isoformat(),
        events=classified,
        total_tracked_minutes=total_tracked,
        total_billable_minutes=total_billable,
        total_non_billable_minutes=total_non_billable,
        skipped_count=skipped_count,
        low_confidence_count=low_conf_count,
    )


def write_output(day: DayClassification) -> Path:
    """Write classified events to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{day.date}.json"
    output_path.write_text(day.model_dump_json(indent=2))
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and classify Google Calendar events for time tracking",
        usage="pull-my-time-for [date] [--week]",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="Target date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--week",
        action="store_true",
        help="Process Mon-Fri of the week containing the given date (or today).",
    )
    args = parser.parse_args()

    if args.week:
        ref = date.fromisoformat(args.date) if args.date else date.today()
        dates = _get_week_dates(ref)
    elif args.date:
        dates = [date.fromisoformat(args.date)]
    else:
        dates = [date.today()]

    for target_date in dates:
        try:
            day = process_date(target_date)
            output_path = write_output(day)
            print_day_summary(day)
            console.print(f"[green]Written to {output_path}[/green]")
            slack_token = os.environ.get("SLACK_BOT_TOKEN")
            slack_user_id = os.environ.get("SLACK_USER_ID")
            if slack_token and slack_user_id:
                from .slack_notifier import send_day_summary
                if send_day_summary(day, slack_user_id, slack_token):
                    console.print("[green]✓ Slack notification sent[/green]")
        except Exception as e:
            console.print(f"[red]Error processing {target_date}: {e}[/red]")
            if len(dates) == 1:
                sys.exit(1)


if __name__ == "__main__":
    main()
