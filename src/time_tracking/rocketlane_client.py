"""Rocketlane API client for time entries."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .config import OVERHEAD_PHASES, OVERHEAD_PROJECT_ID

load_dotenv()

ROCKETLANE_API_BASE = "https://api.rocketlane.com/api/1.0"
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"


def _get_api_key(api_key: str | None = None) -> str:
    if api_key:
        return api_key
    # Try any per-user key, then legacy fallback
    for env_name, val in os.environ.items():
        if env_name.startswith("ROCKETLANE_API_KEY_") and val:
            return val
    key = os.environ.get("ROCKETLANE_API_KEY")
    if key:
        return key
    raise ValueError(
        "No Rocketlane API key found. Set ROCKETLANE_API_KEY_<USER> in .env."
    )


def _request(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
    json_body: dict | None = None,
    api_key: str | None = None,
) -> dict:
    """Make an authenticated request to the Rocketlane API.

    Args:
        api_key: Explicit API key. When None, falls back to env vars.
    """
    url = f"{ROCKETLANE_API_BASE}{endpoint}"
    headers = {
        "api-key": _get_api_key(api_key),
        "accept": "application/json",
        "content-type": "application/json",
    }

    transport = httpx.HTTPTransport(retries=3)
    with httpx.Client(transport=transport, timeout=30.0) as client:
        response = client.request(method, url, headers=headers, params=params, json=json_body)

        if response.status_code == 429:
            retry_after = response.headers.get("X-Retry-After")
            if retry_after:
                wait_until = int(retry_after) / 1000
                sleep_time = max(0, wait_until - time.time())
                time.sleep(min(sleep_time, 60))
            else:
                time.sleep(5)
            response = client.request(method, url, headers=headers, params=params, json=json_body)

        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()


# ---------------------------------------------------------------------------
# Phase resolution
# ---------------------------------------------------------------------------

def resolve_overhead_phases() -> dict[str, int]:
    """Fetch phases for the Overhead project and match to config names.

    Returns a mapping of phase name -> phase ID.
    Caches the result locally.
    """
    cache_path = CACHE_DIR / "overhead_phases.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    result = _request("/phases", params={"projectId": OVERHEAD_PROJECT_ID, "pageSize": 100})
    phases = result.get("data", [])

    phase_map: dict[str, int] = {}
    for phase in phases:
        name = phase.get("phaseName", "")
        phase_id = phase.get("phaseId")
        if name and phase_id:
            phase_map[name] = phase_id

    # Save cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(phase_map, indent=2))

    return phase_map


def populate_overhead_phase_ids() -> None:
    """Populate the phase IDs in OVERHEAD_PHASES from Rocketlane API."""
    phase_map = resolve_overhead_phases()
    for phase in OVERHEAD_PHASES:
        if phase.name in phase_map:
            phase.phase_id = phase_map[phase.name]
        else:
            # Try fuzzy match
            for api_name, api_id in phase_map.items():
                if phase.name.lower() in api_name.lower() or api_name.lower() in phase.name.lower():
                    phase.phase_id = api_id
                    break


# ---------------------------------------------------------------------------
# Time entry operations
# ---------------------------------------------------------------------------

def get_time_entries(date_str: str, api_key: str | None = None) -> list[dict]:
    """Get existing time entries for a specific date."""
    result = _request(
        "/time-entries",
        params={"date.eq": date_str, "pageSize": 100},
        api_key=api_key,
    )
    return result.get("data", [])


def create_time_entry(
    date_str: str,
    minutes: int,
    notes: str,
    billable: bool,
    project_id: int | None = None,
    phase_id: int | None = None,
    category_id: int | None = None,
    api_key: str | None = None,
) -> dict:
    """Create a time entry in Rocketlane.

    Only one of project, phase, or task can be set (API constraint).
    We prefer phase if available, otherwise project.
    """
    body: dict = {
        "date": date_str,
        "minutes": minutes,
        "notes": notes,
        "billable": billable,
    }

    # Only one source field allowed
    if phase_id:
        body["projectPhase"] = {"phaseId": phase_id}
    elif project_id:
        body["project"] = {"projectId": project_id}

    if category_id:
        body["category"] = {"categoryId": category_id}

    return _request("/time-entries", method="POST", json_body=body, api_key=api_key)


def get_all_projects() -> list[dict]:
    """Fetch all Rocketlane projects, cached to cache/projects.json."""
    cache_path = CACHE_DIR / "projects.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    all_projects: list[dict] = []
    page_token = None
    while True:
        params: dict = {"pageSize": 100}
        if page_token:
            params["pageToken"] = page_token
        result = _request("/projects", params=params)
        all_projects.extend(result.get("data", []))
        pagination = result.get("pagination", {})
        if not pagination.get("hasMore"):
            break
        page_token = pagination.get("nextPageToken")
        if not page_token:
            break

    simplified = [
        {"project_id": p["projectId"], "project_name": p["projectName"]}
        for p in all_projects
        if p.get("projectId") and p.get("projectName")
    ]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(simplified, indent=2))
    return simplified


def suggest_projects(domain: str, title: str, n: int = 5) -> list[dict]:
    """Return top-N Rocketlane projects matching a domain/title.

    Scores by word overlap: domain words weighted 3x, title words 1x.
    """
    projects = get_all_projects()
    company = domain.split(".")[0].lower()  # "newclient.com" → "newclient"
    title_words = set(title.lower().split())

    scored: list[tuple[int, dict]] = []
    for proj in projects:
        name_lower = proj["project_name"].lower()
        score = 0
        # Domain company word match
        if company in name_lower:
            score += 3
        # Title word matches
        score += sum(1 for w in title_words if len(w) > 3 and w in name_lower)
        scored.append((score, proj))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:n]]


def resolve_phases_for_project(project_id: int) -> dict[str, int]:
    """Fetch phases for any project and return a name→ID mapping.

    Results are cached to cache/phases_{project_id}.json.
    """
    cache_path = CACHE_DIR / f"phases_{project_id}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    result = _request("/phases", params={"projectId": project_id, "pageSize": 100})
    phases = result.get("data", [])

    phase_map: dict[str, int] = {}
    for phase in phases:
        name = phase.get("phaseName", "")
        phase_id = phase.get("phaseId")
        if name and phase_id:
            phase_map[name] = phase_id

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(phase_map, indent=2))
    return phase_map


def get_phase_id(project_id: int, phase_name: str) -> int | None:
    """Look up a phase ID by project ID and phase name. Uses cached data."""
    phase_map = resolve_phases_for_project(project_id)
    if phase_name in phase_map:
        return phase_map[phase_name]
    # Fuzzy fallback
    for name, pid in phase_map.items():
        if phase_name.lower() in name.lower() or name.lower() in phase_name.lower():
            return pid
    return None


def auto_phase_for_project(project_id: int, title: str) -> int | None:
    """Pick the best-matching phase for a project using the event title.

    Scores each phase by how many title words appear in the phase name.
    Falls back to the first phase if no words match. Returns None only if
    the project has no phases at all.
    """
    phase_map = resolve_phases_for_project(project_id)
    if not phase_map:
        return None

    title_words = set(title.lower().split())
    best_id: int | None = None
    best_score = -1

    for name, pid in phase_map.items():
        name_lower = name.lower()
        score = sum(1 for w in title_words if w in name_lower)
        if score > best_score:
            best_score = score
            best_id = pid

    return best_id


def update_time_entry(
    entry_id: int,
    phase_id: int | None = None,
    project_id: int | None = None,
    category_id: int | None = None,
    notes: str | None = None,
) -> dict:
    """Update an existing time entry in Rocketlane."""
    body: dict = {}
    if phase_id:
        body["projectPhase"] = {"phaseId": phase_id}
    elif project_id:
        body["project"] = {"projectId": project_id}
    if category_id:
        body["category"] = {"categoryId": category_id}
    if notes is not None:
        body["notes"] = notes
    return _request(f"/time-entries/{entry_id}", method="PUT", json_body=body)


def check_duplicates(date_str: str, entries_to_post: list[dict], api_key: str | None = None) -> list[dict]:
    """Check for existing entries and return only new ones.

    Matches by (minutes, project_id, phase_id, category_id) since the API
    does not return notes in time entry list responses.
    """
    existing = get_time_entries(date_str, api_key=api_key)
    existing_keys = {
        (
            e.get("minutes", 0),
            e.get("project", {}).get("projectId"),
            (e.get("projectPhase") or {}).get("phaseId"),
            (e.get("category") or {}).get("categoryId"),
        )
        for e in existing
    }

    new_entries = []
    for entry in entries_to_post:
        key = (
            entry.get("minutes", 0),
            entry.get("project_id"),
            entry.get("phase_id"),
            entry.get("category_id"),
        )
        if key in existing_keys:
            continue
        new_entries.append(entry)

    skipped = len(entries_to_post) - len(new_entries)
    if skipped:
        from .display import console
        console.print(f"[yellow]Skipped {skipped} duplicate entries already in Rocketlane.[/yellow]")

    return new_entries
