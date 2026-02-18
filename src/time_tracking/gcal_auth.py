"""Google Calendar OAuth2 desktop flow."""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Paths relative to the time-tracking project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TOKEN_PATH = _PROJECT_ROOT / "token.json"
CREDENTIALS_PATH = _PROJECT_ROOT / "credentials.json"


def get_credentials() -> Credentials:
    """Get valid Google OAuth2 credentials, refreshing or prompting as needed."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_PATH}. Download OAuth credentials from "
                "Google Cloud Console → APIs & Services → Credentials → "
                "Create OAuth 2.0 Client ID (Desktop app)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    return creds
