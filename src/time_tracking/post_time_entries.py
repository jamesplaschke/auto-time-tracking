"""Script 2: Read classified JSON, confirm, and POST time entries to Rocketlane."""

from __future__ import annotations

from .auto_update import auto_update

auto_update()

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from .config import CATEGORY_INVESTMENT, CATEGORY_REPORTABLE, NON_BILLABLE_ROCKETLANE_PROJECTS
from .display import console, print_post_preview
from .models import ClassifiedEvent, Confidence, DayClassification
from .rocketlane_client import (
    auto_phase_for_project,
    check_duplicates,
    create_time_entry,
    get_phase_id,
    populate_overhead_phase_ids,
)
from .users import UserConfig, get_default_user, resolve_users


def _get_week_dates(ref_date: date) -> list[date]:
    """Get Mon-Fri of the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def _load_classified(date_str: str, user: UserConfig | None = None) -> DayClassification | None:
    """Load classified events from JSON output file."""
    if user:
        path = user.output_dir / f"{date_str}.json"
    else:
        # Legacy fallback
        path = Path(__file__).resolve().parent.parent.parent / "output" / f"{date_str}.json"
    if not path.exists():
        console.print(f"[red]No classified file found: {path}[/red]")
        console.print(f"[dim]Run 'pull-my-time-for {date_str}' first.[/dim]")
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


def _build_entries(day: DayClassification, api_key: str | None = None) -> list[dict]:
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
                else:
                    from .models import ProjectMapping
                    classified.project = ProjectMapping(
                        project_id=override["project_id"],
                        project_name=override.get("project_name", ""),
                        phase_id=override.get("phase_id"),
                        phase_name=override.get("phase_name"),
                    )
            if "phase_id" in override:
                if classified.project:
                    classified.project.phase_id = override["phase_id"]
            if "phase_name" in override and classified.project:
                classified.project.phase_name = override["phase_name"]
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
        # Auto-detect phase from API when no phase is configured for this project
        if not phase_id:
            phase_id = auto_phase_for_project(classified.project.project_id, classified.notes or "")

        # Rocketlane rejects billable=True for projects with a non-billable budget
        rocketlane_billable = classified.billable
        if classified.project.project_id in NON_BILLABLE_ROCKETLANE_PROJECTS:
            rocketlane_billable = False

        entry = {
            "date": day.date,
            "minutes": classified.duration_minutes,
            "notes": classified.notes,
            "billable": rocketlane_billable,
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


def _post_entries(entries: list[dict], dry_run: bool = False, api_key: str | None = None) -> None:
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
                api_key=api_key,
            )
            entry_id = result.get("timeEntryId", "?")
            console.print(f"  [green]✓[/green] {entry['notes'][:40]} → ID {entry_id}")
            success += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] {entry['notes'][:40]} → {e}")
            failed += 1

    console.print()
    console.print(f"[bold]Done:[/bold] {success} posted, {failed} failed.")


def post_day(day: DayClassification, api_key: str | None = None) -> tuple[int, int]:
    """Post a DayClassification to Rocketlane without any prompts or console output.

    Returns (posted_count, skipped_count). Raises on hard errors.
    Intended for programmatic use from slack_listener.py.
    """
    entries = _build_entries(day, api_key=api_key)
    if not entries:
        return 0, 0

    entries = check_duplicates(day.date, entries, api_key=api_key)
    if not entries:
        return 0, 0

    posted = 0
    skipped = 0
    for entry in entries:
        try:
            create_time_entry(
                date_str=entry["date"],
                minutes=entry["minutes"],
                notes=entry["notes"],
                billable=entry["billable"],
                project_id=entry.get("project_id"),
                phase_id=entry.get("phase_id"),
                category_id=entry.get("category_id"),
                api_key=api_key,
            )
            posted += 1
        except Exception:
            skipped += 1

    return posted, skipped


def process_date(
    date_str: str,
    dry_run: bool = False,
    yes: bool = False,
    user: UserConfig | None = None,
) -> None:
    """Process a single date: load, build entries, confirm, post."""
    api_key = user.rocketlane_api_key if user else None

    day = _load_classified(date_str, user=user)
    if not day:
        return

    entries = _build_entries(day, api_key=api_key)
    if not entries:
        console.print(f"[dim]No entries to post for {date_str}.[/dim]")
        return

    # Check for duplicates (skip in dry-run to avoid unnecessary API calls)
    if not dry_run:
        entries = check_duplicates(date_str, entries, api_key=api_key)
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

    _post_entries(entries, api_key=api_key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post classified time entries to Rocketlane",
        usage="post-my-time-for [date] [--week] [--dry-run] [-y] [--user USER]",
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
        help="Post Mon-Fri of the week containing the given date (or today).",
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
    parser.add_argument(
        "--user",
        default=None,
        help="User to process (james/kevin/all). Defaults to james.",
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

    users = resolve_users(args.user)

    for user in users:
        if len(users) > 1:
            console.print(f"\n[bold]Processing user: {user.user_id}[/bold]")

        for date_str in dates:
            if isinstance(date_str, date):
                date_str = date_str.isoformat()
            try:
                process_date(date_str, dry_run=args.dry_run, yes=args.yes, user=user)
            except Exception as e:
                console.print(f"[red]Error processing {date_str} for {user.user_id}: {e}[/red]")
                if len(dates) == 1 and len(users) == 1:
                    sys.exit(1)


if __name__ == "__main__":
    main()
