"""Per-user correction memory — persist Slack corrections and replay on future classifications."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Confidence, DayClassification

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CORRECTIONS_DIR = BASE_DIR / "corrections"


def load_memories(user_id: str) -> list[dict]:
    """Load stored corrections for a user. Returns empty list if no file exists."""
    path = CORRECTIONS_DIR / f"{user_id}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_memories(user_id: str, memories: list[dict]) -> None:
    """Atomic write of memories list to corrections/{user_id}.json."""
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = CORRECTIONS_DIR / f"{user_id}.json"

    fd, tmp_path = tempfile.mkstemp(dir=CORRECTIONS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(memories, f, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def upsert_memories(user_id: str, changes: list[dict], original_text: str) -> int:
    """Add or update memory entries from a correction's changes list.

    Deduplicates by title_pattern (case-insensitive) — latest wins.
    Returns the number of entries upserted.
    """
    memories = load_memories(user_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    upserted = 0

    for change in changes:
        title_pattern = (change.get("event_title") or "").strip().lower()
        if not title_pattern:
            continue

        entry = {
            "title_pattern": title_pattern,
            "action": change.get("action", "reclassify"),
            "project_id": change.get("project_id"),
            "project_name": change.get("project_name"),
            "phase_name": change.get("phase_name"),
            "billable": change.get("billable", False),
            "billable_type": change.get("billable_type"),
            "created_at": now,
            "original_text": original_text,
        }

        # Dedup: replace existing entry with same title_pattern
        memories = [m for m in memories if m.get("title_pattern", "").lower() != title_pattern]
        memories.append(entry)
        upserted += 1

    if upserted:
        save_memories(user_id, memories)

    return upserted


def apply_memories(day: DayClassification, user_id: str) -> DayClassification:
    """Apply stored corrections to matching events.

    Skips events that already have a user_override set (current-session
    corrections take precedence over memory).
    """
    memories = load_memories(user_id)
    if not memories:
        return day

    for event in day.events:
        if event.user_override:
            continue

        title_lower = event.event.title.lower()
        for mem in memories:
            pattern = mem.get("title_pattern", "")
            if not pattern or pattern not in title_lower:
                continue

            override: dict = {}
            action = mem.get("action", "reclassify")

            if action == "skip":
                override["skip"] = True
            elif action == "mark_reportable":
                override["billable"] = True
                override["billable_type"] = "reportable"
            elif action == "mark_investment":
                override["billable"] = True
                override["billable_type"] = "investment"
            elif action == "reclassify":
                if mem.get("project_id") is not None:
                    override["project_id"] = mem["project_id"]
                if mem.get("project_name"):
                    override["project_name"] = mem["project_name"]
                if mem.get("phase_name"):
                    override["phase_name"] = mem["phase_name"]
                if "billable" in mem:
                    override["billable"] = mem["billable"]
                if mem.get("billable_type"):
                    override["billable_type"] = mem["billable_type"]

            if override:
                event.user_override = override
                event.confidence = Confidence.HIGH
                break  # first matching memory wins

    return day
