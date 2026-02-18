"""Rich CLI table formatting for time tracking output."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .models import ClassifiedEvent, Confidence, DayClassification

console = Console()


def print_day_summary(day: DayClassification) -> None:
    """Print a summary table for a classified day."""
    console.print()
    console.print(f"[bold]Time Tracking Summary: {day.date}[/bold]")
    console.print()

    # Tracked events table
    tracked = [e for e in day.events if not e.skip]
    if tracked:
        table = Table(title="Tracked Events", show_lines=True)
        table.add_column("Time", style="dim", width=13)
        table.add_column("Title", width=35)
        table.add_column("Category", width=25)
        table.add_column("Min", justify="right", width=5)
        table.add_column("Billable", justify="center", width=8)
        table.add_column("Conf.", justify="center", width=6)

        for e in sorted(tracked, key=lambda x: x.event.start):
            start = e.event.start.strftime("%H:%M")
            end = e.event.end.strftime("%H:%M")
            time_str = f"{start}-{end}"

            billable_str = "[green]Yes[/green]" if e.billable else "[dim]No[/dim]"
            conf_str = (
                "[green]High[/green]"
                if e.confidence == Confidence.HIGH
                else "[yellow]Low[/yellow]"
            )

            title = e.event.title
            if len(title) > 35:
                title = title[:32] + "..."

            table.add_row(
                time_str,
                title,
                e.category,
                str(e.duration_minutes),
                billable_str,
                conf_str,
            )

        console.print(table)
    else:
        console.print("[dim]No tracked events.[/dim]")

    # Skipped events table
    skipped = [e for e in day.events if e.skip]
    if skipped:
        console.print()
        skip_table = Table(title="Skipped Events", show_lines=False)
        skip_table.add_column("Time", style="dim", width=13)
        skip_table.add_column("Title", width=35)
        skip_table.add_column("Reason", style="dim", width=30)

        for e in sorted(skipped, key=lambda x: x.event.start):
            start = e.event.start.strftime("%H:%M")
            end = e.event.end.strftime("%H:%M")
            time_str = f"{start}-{end}" if not e.event.all_day else "All day"

            title = e.event.title
            if len(title) > 35:
                title = title[:32] + "..."

            skip_table.add_row(time_str, title, e.skip_reason or "")

        console.print(skip_table)

    # Summary stats
    console.print()
    console.print(f"  Total tracked:      [bold]{day.total_tracked_minutes}[/bold] min ({day.total_tracked_minutes / 60:.1f} hrs)")
    console.print(f"  Billable:           [green]{day.total_billable_minutes}[/green] min ({day.total_billable_minutes / 60:.1f} hrs)")
    console.print(f"  Non-billable:       {day.total_non_billable_minutes} min ({day.total_non_billable_minutes / 60:.1f} hrs)")
    console.print(f"  Skipped:            {day.skipped_count} events")

    if day.low_confidence_count > 0:
        console.print(
            f"  [yellow]Low confidence:     {day.low_confidence_count} events (review in output JSON)[/yellow]"
        )
    console.print()


def print_post_preview(entries: list[dict], date_str: str) -> None:
    """Print a preview table of time entries to be posted."""
    console.print()
    console.print(f"[bold]Time Entries to Post: {date_str}[/bold]")
    console.print()

    if not entries:
        console.print("[dim]No entries to post.[/dim]")
        return

    table = Table(show_lines=True)
    table.add_column("Project", width=30)
    table.add_column("Phase", width=20)
    table.add_column("Notes", width=30)
    table.add_column("Min", justify="right", width=5)
    table.add_column("Billable", justify="center", width=8)

    total_min = 0
    for entry in entries:
        billable_str = "[green]Yes[/green]" if entry.get("billable") else "[dim]No[/dim]"
        notes = entry.get("notes", "")
        if len(notes) > 30:
            notes = notes[:27] + "..."
        table.add_row(
            entry.get("project_name", "—"),
            entry.get("phase_name", "—"),
            notes,
            str(entry.get("minutes", 0)),
            billable_str,
        )
        total_min += entry.get("minutes", 0)

    console.print(table)
    console.print(f"\n  Total: [bold]{total_min}[/bold] min ({total_min / 60:.1f} hrs)")
    console.print()
