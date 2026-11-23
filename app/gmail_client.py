"""Gmail API helper: login (OAuth), unread mails fetch, aur reply draft save."""
import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# readonly = mails padhna, compose = draft banana (send nahi karta)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"


def get_service():
    """Login karo (pehli baar browser khulega) aur Gmail service return karo."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload) -> str:
    """Mail ke payload se plain text body nikalo (nested parts handle karta hai)."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


def fetch_unread(max_results: int = 5) -> list[dict]:
    """Inbox ki unread mails fetch karo."""
    service = get_service()
    resp = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread in:inbox", maxResults=max_results)
        .execute()
    )

    mails = []
    for item in resp.get("messages", []):
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        mails.append(
            {
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "message_id": headers.get("message-id", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", "(no subject)"),
                "date": headers.get("date", ""),
                "body": _extract_body(msg["payload"]).strip(),
            }
        )
    return mails


def create_draft(mail: dict, reply_text: str) -> str:
    """Reply ko Gmail Drafts mein save karo (bhejta nahi). Draft ka id return karta hai."""
    service = get_service()

    subject = mail["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = EmailMessage()
    msg["To"] = mail["from"]
    msg["Subject"] = subject
    if mail.get("message_id"):
        # Isse reply usi thread mein jata hai
        msg["In-Reply-To"] = mail["message_id"]
        msg["References"] = mail["message_id"]
    msg.set_content(reply_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw, "threadId": mail["thread_id"]}})
        .execute()
    )
    return draft["id"]