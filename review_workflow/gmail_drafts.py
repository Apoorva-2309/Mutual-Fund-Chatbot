
from pathlib import Path
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailConfigError(RuntimeError):
    """User-facing Gmail configuration error. Must never include secrets."""


def _secret_field(mapping, name):
    try:
        if name not in mapping:
            return None
        value = mapping[name]
    except Exception:
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _gmail_secrets_info():
    try:
        import streamlit as st

        gmail = st.secrets["gmail"]
    except Exception:
        return None

    if gmail is None:
        return None

    return {
        "client_id": _secret_field(gmail, "client_id"),
        "client_secret": _secret_field(gmail, "client_secret"),
        "refresh_token": _secret_field(gmail, "refresh_token"),
        "token": _secret_field(gmail, "token"),
        "token_uri": _secret_field(gmail, "token_uri") or TOKEN_URI,
    }


def gmail_is_configured() -> bool:
    if TOKEN_FILE.exists():
        return True
    info = _gmail_secrets_info()
    return bool(
        info
        and info.get("client_id")
        and info.get("client_secret")
        and info.get("refresh_token")
    )


def _load_credentials():
    persist_refresh = False

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), SCOPES
        )
        persist_refresh = True
    else:
        info = _gmail_secrets_info()
        if not info or not all(
            [
                info.get("client_id"),
                info.get("client_secret"),
                info.get("refresh_token"),
            ]
        ):
            raise GmailConfigError(
                "Gmail is not configured. Locally, run gmail_auth.py to "
                "create token.json. On Streamlit Cloud, add a [gmail] "
                "section in secrets with client_id, client_secret, and "
                "refresh_token."
            )
        credentials = Credentials(
            token=info.get("token"),
            refresh_token=info["refresh_token"],
            token_uri=info.get("token_uri") or TOKEN_URI,
            client_id=info["client_id"],
            client_secret=info["client_secret"],
            scopes=SCOPES,
        )

    try:
        if not credentials.valid:
            if not credentials.refresh_token:
                raise GmailConfigError(
                    "Gmail authorization is invalid and cannot be refreshed. "
                    "Run gmail_auth.py locally, or update refresh_token in "
                    "Streamlit secrets."
                )
            credentials.refresh(Request())
            if persist_refresh:
                TOKEN_FILE.write_text(
                    credentials.to_json(), encoding="utf-8"
                )
    except GmailConfigError:
        raise
    except Exception:
        raise GmailConfigError(
            "Gmail authorization is expired or invalid and could not be "
            "refreshed. Run gmail_auth.py locally, or update client_id, "
            "client_secret, and refresh_token in Streamlit secrets."
        ) from None

    if not credentials.valid:
        raise GmailConfigError(
            "Gmail authorization is invalid. Run gmail_auth.py locally, "
            "or update Streamlit secrets."
        )

    return credentials


def create_gmail_draft(to_email: str, subject: str, body: str) -> str:
    """Create a Gmail draft. This function never sends an email."""

    if not to_email.strip() or not subject.strip() or not body.strip():
        raise ValueError("Recipient, subject, and body are required.")

    credentials = _load_credentials()

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    try:
        service = build(
            "gmail", "v1", credentials=credentials,
            cache_discovery=False
        )
        result = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw_message}},
        ).execute()
    except GmailConfigError:
        raise
    except Exception:
        raise GmailConfigError(
            "Gmail did not confirm draft creation. Check Gmail Drafts "
            "before retrying. If this continues, re-authorize Gmail."
        ) from None

    draft_id = result.get("id") if isinstance(result, dict) else None
    if not draft_id:
        raise GmailConfigError(
            "Gmail did not return a draft ID. Check Gmail Drafts "
            "before retrying."
        )
    return draft_id
