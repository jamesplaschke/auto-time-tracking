"""Script 2: Read classified JSON, confirm, and POST time entries to Rocketlane."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from .config import CATEGORY_INVESTMENT, CATEGORY_REPORTABLE
from .display import console, print_post_preview
from .models import ClassifiedEvent, Confidence, DayClassification
from .rocketlane_client import (
    check_duplicates,
    create_time_entry,
    get_phase_id,
    populate_overhead_phase_ids,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _get_week_dates(ref_date: date) -> list[date]:
    """Get Mon-Fri of the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def _load_classified(date_str: str) -> DayClassification | None:
    """Load classified events from JSON output file."""
    path = OUTPUT_DIR / f"{date_str}.json"
    if not path.exists():
        console.print(f"[red]No classified file found: {path}[/red]")
        console.print("[dim]Run 'uv run classify --date {date_str}' first.[/dim]")
        return None
    data = json.loads(path.read_text())
    return DayClassification.model_validate(data)


def _category_id_for(classified: ClassifiedEvent) -> int:
    """Derive the Rocketlane category ID from the classified event.

    Only two categories are configured: Reportable (125238) and Investment (125235).
    Billable reportable → Reportable; everything else → Investment (Not-Reportable).
    """
    if classified.billable and (
        not classified.billable_type or classified.billable_type.value == "reportable"
    ):
        return CATEGORY_REPORTABLE
    return CATEGORY_INVESTMENT


def _build_entries(day: DayClassification) -> list[dict]:
    """Build list of time entry dicts from classified events."""
    entries = []
    low_conf_skipped = 0

    for classified in day.events:
        if classified.skip:
            continue
        if classified.duration_minutes <= 0:
            continue

        # Apply user overrides if present
        if classified.user_override:
            override = classified.user_override
            if override.get("skip"):
                continue
            if "billable" in override:
                classified.billable = override["billable"]
            if "project_id" in override:
                if classified.project:
                    classified.project.project_id = override["project_id"]
            if "phase_id" in override:
                if classified.project:
                    classified.project.phase_id = override["phase_id"]
            if "notes" in override:
                classified.notes = override["notes"]
            if "category" in override:
                classified.category = override["category"]
            # Mark as overridden (high confidence now)
            classified.confidence = Confidence.HIGH

        # Warn about low-confidence events without overrides
        if classified.confidence == Confidence.LOW and not classified.user_override:
            console.print(
                f"[yellow]Skipping low-confidence event (no override): "
                f"{classified.event.title} ({classified.category})[/yellow]"
            )
            low_conf_skipped += 1
            continue

        if not classified.project:
            console.print(
                f"[yellow]Skipping event with no project mapping: "
                f"{classified.event.title}[/yellow]"
            )
            continue

        # Resolve phase_id from phase_name if not already set
        phase_id = classified.project.phase_id
        phase_name = classified.project.phase_name
        if (not phase_id) and phase_name:
            phase_id = get_phase_id(classified.project.project_id, phase_name)

        entry = {
            "date": day.date,
            "minutes": classified.duration_minutes,
            "notes": classified.notes,
            "billable": classified.billable,
            "project_id": classified.project.project_id,
            "phase_id": phase_id,
            "project_name": classified.project.project_name,
            "phase_name": phase_name or "—",
            "category_id": _category_id_for(classified),
        }
        entries.append(entry)

    if low_conf_skipped:
        console.print(
            f"[yellow]Total low-confidence events skipped: {low_conf_skipped}. "
            f"Add 'user_override' in the JSON to include them.[/yellow]"
        )

    return entries


def _post_entries(entries: list[dict], dry_run: bool = False) -> None:
    """Post time entries to Rocketlane."""
    if not entries:
        console.print("[dim]Nothing to post.[/dim]")
        return

    if dry_run:
        console.print("[bold yellow]DRY RUN — nothing will be posted.[/bold yellow]")
        return

    console.print(f"Posting {len(entries)} time entries...")
    success = 0
    failed = 0

    for entry in entries:
        try:
            result = create_time_entry(
                date_str=entry["date"],
                minutes=entry["minutes"],
                notes=entry["notes"],
                billable=entry["billable"],
                project_id=entry.get("project_id"),
                phase_id=entry.get("phase_id"),
                category_id=entry.get("category_id"),
            )
            entry_id = result.get("timeEntryId", "?")
            console.print(f"  [green]✓[/green] {entry['notes'][:40]} → ID {entry_id}")
            success += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] {entry['notes'][:40]} → {e}")
            failed += 1

    console.print()
    console.print(f"[bold]Done:[/bold] {success} posted, {failed} failed.")


def process_date(date_str: str, dry_run: bool = False, yes: bool = False) -> None:
    """Process a single date: load, build entries, confirm, post."""
    day = _load_classified(date_str)
    if not day:
        return

    entries = _build_entries(day)
    if not entries:
        console.print(f"[dim]No entries to post for {date_str}.[/dim]")
        return

    # Check for duplicates (skip in dry-run to avoid unnecessary API calls)
    if not dry_run:
        entries = check_duplicates(date_str, entries)
        if not entries:
            console.print(f"[dim]All entries already exist for {date_str}.[/dim]")
            return

    print_post_preview(entries, date_str)

    if dry_run:
        console.print("[bold yellow]DRY RUN — nothing will be posted.[/bold yellow]")
        return

    # Confirm
    if not yes:
        confirm = input("Post these entries? [y/N] ").strip().lower()
        if confirm != "y":
            console.print("[dim]Cancelled.[/dim]")
            return

    _post_entries(entries)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post classified time entries to Rocketlane"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--week",
        action="store_true",
        help="Post Mon-Fri of the current week.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be posted without actually posting.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()

    # Resolve overhead phase IDs from Rocketlane API
    if not args.dry_run:
        try:
            populate_overhead_phase_ids()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not resolve overhead phases: {e}[/yellow]")

    if args.week:
        ref = date.fromisoformat(args.date) if args.date else date.today()
        dates = _get_week_dates(ref)
    elif args.date:
        dates = [args.date]
    else:
        dates = [date.today().isoformat()]

    for date_str in dates:
        if isinstance(date_str, date):
            date_str = date_str.isoformat()
        try:
            process_date(date_str, dry_run=args.dry_run, yes=args.yes)
        except Exception as e:
            console.print(f"[red]Error processing {date_str}: {e}[/red]")
            if len(dates) == 1:
                sys.exit(1)


if __name__ == "__main__":
    main()
