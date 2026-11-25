"""Gmail API helper: login (OAuth), unread fetch, draft save, send reply, aur label tool."""
import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# readonly = mails padhna, compose = draft banana, send = mail bhejna, modify = label lagana
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

LABEL_NAME = "AI-Processed"

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
    """Inbox ki unread mails fetch karo (jin par AI-Processed label nahi hai)."""
    service = get_service()
    resp = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=f"is:unread in:inbox -label:{LABEL_NAME}",
            maxResults=max_results,
        )
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
                "reply_to": headers.get("reply-to", ""),
                "subject": headers.get("subject", "(no subject)"),
                "date": headers.get("date", ""),
                "body": _extract_body(msg["payload"]).strip(),
            }
        )
    return mails


def _build_reply_message(mail: dict, reply_text: str) -> dict:
    """Reply ka Gmail-format message body banao (draft aur send dono yahi use karte hain)."""
    subject = mail["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = EmailMessage()
    msg["To"] = mail.get("reply_to") or mail["from"]
    msg["Subject"] = subject
    if mail.get("message_id"):
        # Isse reply usi thread mein jata hai
        msg["In-Reply-To"] = mail["message_id"]
        msg["References"] = mail["message_id"]
    msg.set_content(reply_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw, "threadId": mail["thread_id"]}


def create_draft(mail: dict, reply_text: str) -> str:
    """Reply ko Gmail Drafts mein save karo (bhejta nahi). Draft ka id return karta hai."""
    service = get_service()
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": _build_reply_message(mail, reply_text)})
        .execute()
    )
    return draft["id"]


def send_reply(mail: dict, reply_text: str) -> str:
    """TOOL: reply asli mein BHEJ do. Sent message ka id return karta hai.

    Sirf approval ke baad hi call hona chahiye (graph.py mein approve node ke baad).
    """
    service = get_service()
    sent = (
        service.users()
        .messages()
        .send(userId="me", body=_build_reply_message(mail, reply_text))
        .execute()
    )
    return sent["id"]


def reply_address(mail: dict) -> str:
    """Reply kis address par jayegi (approval screen par dikhane ke liye)."""
    return mail.get("reply_to") or mail["from"]


def _get_or_create_label(service, name: str = LABEL_NAME) -> str:
    """Label ka id dhundo, na mile to naya bana do."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]

    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def mark_processed(mail_id: str) -> None:
    """TOOL: mail par AI-Processed label lagao, taake agent usay dobara na uthaye."""
    service = get_service()
    label_id = _get_or_create_label(service)
    service.users().messages().modify(
        userId="me", id=mail_id, body={"addLabelIds": [label_id]}
    ).execute()