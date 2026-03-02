"""Interpret free-text corrections using Claude and apply them to DayClassification."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .models import Confidence, DayClassification

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _build_prompt(day: DayClassification, user_text: str) -> str:
    day_json = day.model_dump_json(indent=2)
    return f"""You are a time-tracking classification assistant.

Current day classification for {day.date}:
{day_json}

The user wants to make this correction:
"{user_text}"

Respond with ONLY a valid JSON object (no markdown code fences, no explanation):
{{
  "changes": [
    {{
      "event_title": "exact or partial title to match (case-insensitive substring)",
      "action": "reclassify|skip|mark_reportable|mark_investment",
      "project_id": <int or null>,
      "project_name": "<string or null>",
      "phase_name": "<string or null>",
      "billable": <bool>,
      "billable_type": "<reportable|investment|null>"
    }}
  ],
  "save_as_rule": <bool>,
  "rule": {{
    "location": "SKIP_TITLE_PATTERNS",
    "pattern": "<regex pattern string>",
    "description": "<human-readable description>"
  }},
  "summary": "<one-sentence human-readable summary of all changes>"
}}

Rules:
- "skip" action: set billable=false, project_id=null, project_name=null, phase_name=null
- "reclassify" action: provide project_id, project_name, phase_name, billable, billable_type
- "mark_reportable": billable_type="reportable", billable=true (keep existing project)
- "mark_investment": billable_type="investment", billable=true (keep existing project)
- Only set save_as_rule=true if user explicitly says "always", "save as rule", or "save rule"
- If save_as_rule is false, omit the "rule" key entirely
- Known project IDs: Overhead=1000862, Philips HPM=994649, Vista Robotics=1000461, Enterprise Pod=1000405
- Known overhead phase names: "QM Work", "Non-Project Meetings", "Enabling Work", "Other Overhead"
- Match event_title case-insensitively as a substring of the event title
"""


def _apply_changes(day: DayClassification, changes: list[dict]) -> DayClassification:
    """Apply structured changes to matching events via user_override."""
    for change in changes:
        title_pattern = change.get("event_title", "").lower()
        action = change.get("action", "reclassify")

        for event in day.events:
            if title_pattern and title_pattern not in event.event.title.lower():
                continue

            override = dict(event.user_override or {})

            if action == "skip":
                override["skip"] = True
            elif action == "mark_reportable":
                override["billable"] = True
                override["billable_type"] = "reportable"
            elif action == "mark_investment":
                override["billable"] = True
                override["billable_type"] = "investment"
            elif action == "reclassify":
                if change.get("project_id") is not None:
                    override["project_id"] = change["project_id"]
                if change.get("project_name"):
                    override["project_name"] = change["project_name"]
                if change.get("phase_name"):
                    override["phase_name"] = change["phase_name"]
                if "billable" in change:
                    override["billable"] = change["billable"]
                if change.get("billable_type"):
                    override["billable_type"] = change["billable_type"]

            event.user_override = override
            event.confidence = Confidence.HIGH

    return day


def _save_rule(rule: dict) -> None:
    """Persist a classification rule to config.py, CLASSIFICATION_RULES.md, and git push."""
    location = rule.get("location", "")
    pattern = rule.get("pattern", "")
    description = rule.get("description", "Auto-saved rule")

    config_path = BASE_DIR / "src" / "time_tracking" / "config.py"
    rules_path = BASE_DIR / "CLASSIFICATION_RULES.md"
    git_root = BASE_DIR.parent

    # --- Update config.py ---
    config_text = config_path.read_text()
    new_line = f'    re.compile(r"{pattern}", re.IGNORECASE),  # {description}'

    if location == "SKIP_TITLE_PATTERNS":
        list_marker = "SKIP_TITLE_PATTERNS: list[re.Pattern] = ["
        start_idx = config_text.find(list_marker)
        if start_idx != -1:
            close_idx = config_text.find("\n]", start_idx)
            if close_idx != -1:
                config_text = (
                    config_text[:close_idx]
                    + f"\n{new_line}"
                    + config_text[close_idx:]
                )
                config_path.write_text(config_text)

    # --- Update CLASSIFICATION_RULES.md ---
    if rules_path.exists():
        rules_text = rules_path.read_text()
    else:
        rules_text = "# Classification Rules\n\n"

    rules_text += (
        f"\n## Auto-saved rule\n"
        f"- **Pattern:** `{pattern}`\n"
        f"- **Location:** `{location}`\n"
        f"- **Description:** {description}\n"
    )
    rules_path.write_text(rules_text)

    # --- Git commit and push ---
    try:
        subprocess.run(
            ["git", "add",
             str(config_path.relative_to(git_root)),
             str(rules_path.relative_to(git_root))],
            cwd=str(git_root),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Auto-save rule: {description}"],
            cwd=str(git_root),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=str(git_root),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        print(f"Warning: Git operation failed: {stderr or e}")


def interpret_and_apply(
    day: DayClassification,
    user_text: str,
) -> tuple[DayClassification, str, bool, list[dict]]:
    """Parse a free-text correction and apply it to the DayClassification.

    Returns (updated_day, human_readable_summary, save_as_rule, changes).

    Supported corrections (examples):
    - "move vista thinking to overhead"
    - "mark Review philips config as reportable"
    - "skip Ketryx Core Concepts"
    - "always skip wiring to win, save as rule"
    """
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: uv add anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(day, user_text)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON — Claude Haiku should return clean JSON but guard against fences
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise ValueError(
                f"Could not parse Claude response as JSON: {response_text[:200]}"
            )

    changes = result.get("changes", [])
    save_as_rule = result.get("save_as_rule", False)
    summary = result.get("summary", "Applied corrections")

    updated_day = _apply_changes(day, changes)

    if save_as_rule and "rule" in result:
        _save_rule(result["rule"])

    return updated_day, summary, save_as_rule, changes
