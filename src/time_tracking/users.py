"""User registry — per-user configuration for multi-user time tracking."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class UserConfig:
    """Per-user configuration for time tracking."""

    user_id: str  # "james", "kevin"
    email: str  # Google Calendar self-identification
    timezone: str
    slack_user_id: str
    rocketlane_api_key_env: str  # env var name, e.g. "ROCKETLANE_API_KEY_JAMES"
    personal_skip_patterns: list[re.Pattern] = field(default_factory=list)

    @property
    def google_token_path(self) -> Path:
        return _PROJECT_ROOT / "tokens" / f"{self.user_id}.json"

    @property
    def output_dir(self) -> Path:
        return _PROJECT_ROOT / "output" / self.user_id

    @property
    def rocketlane_api_key(self) -> str:
        key = os.environ.get(self.rocketlane_api_key_env)
        if not key:
            raise ValueError(
                f"{self.rocketlane_api_key_env} environment variable is required for user '{self.user_id}'. "
                f"Set it in .env or export it."
            )
        return key


USERS: dict[str, UserConfig] = {
    "adrian": UserConfig(
        user_id="adrian",
        email="adrians@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09FU3WQFA8",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_ADRIAN",
    ),
    "billy": UserConfig(
        user_id="billy",
        email="billy.dempsey@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U0A77Q3G71P",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_BILLY",
    ),
    "charlie": UserConfig(
        user_id="charlie",
        email="charleso@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U07S0DRMX34",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_CHARLIE",
    ),
    "emmap": UserConfig(
        user_id="emmap",
        email="emmap@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09H8VAPMQF",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_EMMAP",
    ),
    "emmar": UserConfig(
        user_id="emmar",
        email="emmar@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U090BUZFWG6",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_EMMAR",
    ),
    "james": UserConfig(
        user_id="james",
        email="jamesp@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09QB926YRK",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_JAMES",
        personal_skip_patterns=[
            re.compile(r"\bwater\s+polo\b", re.IGNORECASE),
        ],
    ),
    "jenn": UserConfig(
        user_id="jenn",
        email="jennd@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U06PGJ4SB8W",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_JENN",
    ),
    "jess": UserConfig(
        user_id="jess",
        email="jessk@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U08P4FKFBA9",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_JESS",
    ),
    "joey": UserConfig(
        user_id="joey",
        email="joeyc@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09AWGCTLTW",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_JOEY",
    ),
    "jolani": UserConfig(
        user_id="jolani",
        email="jolanid@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U0736JZBYR4",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_JOLANI",
    ),
    "kevin": UserConfig(
        user_id="kevin",
        email="kevinb@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09LK0PCAJ1",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_KEVIN",
    ),
    "laura": UserConfig(
        user_id="laura",
        email="laurae@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U07FBJ5T62V",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_LAURA",
    ),
    "lee": UserConfig(
        user_id="lee",
        email="leec@ketryx.com",
        timezone="America/Los_Angeles",
        slack_user_id="U053T6RRKFD",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_LEE",
    ),
    "lidor": UserConfig(
        user_id="lidor",
        email="lidort@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09FU3YR62G",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_LIDOR",
    ),
    "logan": UserConfig(
        user_id="logan",
        email="loganb@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U07Q7ASE9FH",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_LOGAN",
    ),
    "manasa": UserConfig(
        user_id="manasa",
        email="manasak@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U094AH4TD4H",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_MANASA",
    ),
    "matt": UserConfig(
        user_id="matt",
        email="mattdu@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U093E54H9K5",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_MATT",
    ),
    "michael": UserConfig(
        user_id="michael",
        email="michaelre@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09P8JFSASK",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_MICHAEL",
    ),
    "nick": UserConfig(
        user_id="nick",
        email="nicholasb@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U0914GV3339",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_NICK",
    ),
    "rachel": UserConfig(
        user_id="rachel",
        email="rachelg@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U08VA7A2HNV",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_RACHEL",
    ),
    "richard": UserConfig(
        user_id="richard",
        email="richard.schmidt@ketryx.com",
        timezone="America/Chicago",
        slack_user_id="U09U969UZR6",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_RICHARD",
    ),
    "david": UserConfig(
        user_id="david",
        email="davids@ketryx.com",
        timezone="America/Chicago",
        slack_user_id="U06DZ5UGLTH",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_DAVID",
    ),
    "tim": UserConfig(
        user_id="tim",
        email="timb@ketryx.com",
        timezone="America/New_York",
        slack_user_id="U09DRMS72MV",
        rocketlane_api_key_env="ROCKETLANE_API_KEY_TIM",
    ),
}

def get_user(user_id: str) -> UserConfig:
    """Get a user by ID. Raises KeyError if not found."""
    if user_id not in USERS:
        available = ", ".join(USERS.keys())
        raise KeyError(f"Unknown user '{user_id}'. Available users: {available}")
    return USERS[user_id]


def resolve_users(cli_arg: str | None) -> list[UserConfig]:
    """Resolve --user CLI argument to a list of UserConfig objects.

    None → error (--user is required)
    "all" → all registered users
    "james" / "kevin" → that specific user
    """
    if cli_arg is None:
        available = ", ".join(USERS.keys())
        raise SystemExit(
            f"Error: --user is required. Available users: {available}"
        )
    if cli_arg.lower() == "all":
        return list(USERS.values())
    return [get_user(cli_arg.lower())]
