
from pathlib import Path
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def create_gmail_draft(to_email: str, subject: str, body: str) -> str:
    """Create a Gmail draft. This function never sends an email."""

    if not to_email.strip() or not subject.strip() or not body.strip():
        raise ValueError("Recipient, subject, and body are required.")

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            "Gmail token not found. Run gmail_auth.py first."
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_FILE), SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_FILE.write_text(
            credentials.to_json(), encoding="utf-8"
        )

    if not credentials.valid:
        raise RuntimeError(
            "Gmail authorization is invalid. Run gmail_auth.py again."
        )

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    service = build(
        "gmail", "v1", credentials=credentials,
        cache_discovery=False
    )

    result = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw_message}},
    ).execute()

    return result["id"]
