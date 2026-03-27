import base64
import json
import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import ollama

import tracker

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
BROKERS_FILE = "brokers.json"

CLASSIFICATION_PROMPT = """You are classifying an email response from a data broker to a GDPR Article 17 erasure request.

Classify the email as exactly one of:
- done: the broker confirmed that the data has been deleted or the request has been fulfilled
- needs_action: the broker is asking for more information, identity verification, or further steps from the requester
- failed: the broker refused, denied, or stated they cannot process the request
- needs_review: the email is an automated acknowledgement, is unclear, or you are not confident in the classification

Reply with only the classification word, nothing else.

Email:
{body}
"""

NOTIFICATION_MESSAGES = {
    "done": "confirmed deletion",
    "needs_action": "ACTION REQUIRED — broker is asking for more information",
    "failed": "broker refused or denied the request",
    "needs_review": "reply is unclear — please check manually",
}


def get_gmail_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def extract_body(payload: dict) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Multipart: recurse through parts, prefer plain text over HTML
    plain, html = "", ""
    for part in payload.get("parts", []):
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain":
            data = part.get("body", {}).get("data", "")
            plain = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        elif part_mime == "text/html":
            data = part.get("body", {}).get("data", "")
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        elif part_mime.startswith("multipart/"):
            result = extract_body(part)
            if result:
                plain = result

    return plain or html


def classify_with_ollama(body: str) -> str:
    """Send email body to local Ollama model for classification."""
    prompt = CLASSIFICATION_PROMPT.format(body=body[:3000])  # cap at 3000 chars

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    result = response["message"]["content"].strip().lower()

    for valid in ("done", "needs_action", "failed", "needs_review"):
        if valid in result:
            return valid

    return "needs_review"


def submitted_at_to_gmail_date(submitted_at: str) -> str:
    """Convert ISO datetime string to Gmail after: search format (YYYY/MM/DD)."""
    dt = datetime.fromisoformat(submitted_at)
    return dt.strftime("%Y/%m/%d")


def check_broker(service, broker: dict, submitted_at: str) -> str | None:
    """
    Search Gmail for replies from a broker received after submitted_at.
    Returns a classification string or None if no reply found.
    """
    dpo_email = broker.get("dpo_email")
    if not dpo_email:
        return None

    after_date = submitted_at_to_gmail_date(submitted_at)
    query = f"from:{dpo_email} after:{after_date}"

    result = service.users().messages().list(userId="me", q=query).execute()
    messages = result.get("messages", [])

    if not messages:
        return None

    # Use the most recent message (first in list)
    msg = service.users().messages().get(
        userId="me", id=messages[0]["id"], format="full"
    ).execute()

    body = extract_body(msg["payload"])
    if not body.strip():
        return "needs_review"

    return classify_with_ollama(body)


def check_replies():
    """Main entry point: check inbox for broker replies and update tracker."""
    if not os.path.exists(CREDENTIALS_FILE):
        print(
            "[!] credentials.json not found.\n"
            "    See README for Gmail API setup instructions.\n"
        )
        return

    print("Checking inbox for broker replies...\n")

    service = get_gmail_service()

    # Only check brokers that have been sent a request
    sent_brokers = [
        r for r in tracker.get_all()
        if r["status"] == "sent" and r["submitted_at"]
    ]

    if not sent_brokers:
        print("No sent requests to check.\n")
        return

    with open(BROKERS_FILE) as f:
        brokers_by_name = {b["name"]: b for b in json.load(f)["brokers"]}

    updated = 0
    notifications = []

    for record in sent_brokers:
        name = record["broker_name"]
        broker = brokers_by_name.get(name)
        if not broker:
            continue

        classification = check_broker(service, broker, record["submitted_at"])

        if classification:
            note = NOTIFICATION_MESSAGES.get(classification, "")
            tracker.set_status(name, classification, note)
            updated += 1
            print(f"  [{name}] → {classification}")
            if classification in ("needs_action", "needs_review", "failed"):
                notifications.append((name, NOTIFICATION_MESSAGES[classification]))
        else:
            print(f"  [{name}] → no reply yet")

    print(f"\n{updated} broker(s) updated.\n")

    if notifications:
        print("=" * 55)
        print("  ATTENTION — the following brokers require action:")
        print("=" * 55)
        for name, msg in notifications:
            print(f"  ! {name}: {msg}")
        print("=" * 55)
        print()


if __name__ == "__main__":
    tracker.init_db()
    check_replies()
