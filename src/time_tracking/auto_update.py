"""Auto-update: pull latest code and sync deps on every run."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent


def auto_update() -> None:
    """Pull latest changes, sync deps, and re-exec if code changed."""
    # Guard against infinite re-exec loop
    if os.environ.get("_AUTO_UPDATED"):
        return

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
            # Re-exec so the process loads the new code
            os.environ["_AUTO_UPDATED"] = "1"
            os.execvp(sys.argv[0], sys.argv)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # no git, no network, etc. — just skip
