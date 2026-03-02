"""Google Calendar OAuth2 desktop flow."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Paths relative to the time-tracking project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LEGACY_TOKEN_PATH = _PROJECT_ROOT / "token.json"
CREDENTIALS_PATH = _PROJECT_ROOT / "credentials.json"


def get_credentials(token_path: Path | None = None) -> Credentials:
    """Get valid Google OAuth2 credentials, refreshing or prompting as needed.

    Args:
        token_path: Where to store/load the OAuth token. Defaults to the
                    legacy ``token.json`` in the project root.
    """
    if token_path is None:
        token_path = _LEGACY_TOKEN_PATH

    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

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

    # Ensure parent directory exists (e.g. tokens/)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds
