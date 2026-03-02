"""Auto-update: pull latest code and sync deps on every run."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent


def auto_update() -> None:
    """Pull latest changes and sync dependencies. Runs silently."""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return  # offline or conflict — skip silently

        if "Already up to date" not in result.stdout:
            # Something changed — re-sync deps in case pyproject.toml updated
            subprocess.run(
                ["uv", "sync"],
                cwd=REPO_DIR,
                capture_output=True,
                timeout=30,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # no git, no network, etc. — just skip
