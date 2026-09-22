"""
mcp_servers/email_server.py
----------------------------
MCP server exposing Gmail actions as tools:
    - send_email
    - list_recent_emails

This is the "Email Server (Gmail)" box in the architecture diagram.
It speaks MCP over stdio; mcp_client.py launches it as a subprocess,
so you normally never run this file directly.

One-time setup:
    1. In Google Cloud Console, enable the Gmail API and create an
       OAuth "Desktop app" client. Download the JSON as credentials.json
       and place it in the project root.
    2. First run will open a browser to authorize; a gmail_token.json
       is cached afterwards so you won't be prompted again.

Env vars (optional overrides):
    GOOGLE_CREDENTIALS_PATH  (default: credentials.json)
    GMAIL_TOKEN_PATH         (default: gmail_token.json)
"""

import base64
import os
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")

mcp = FastMCP("email-server")


def _get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email through the user's Gmail account.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    service = _get_gmail_service()

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )

    return f"Email sent to {to} (message id: {sent.get('id')})"


@mcp.tool()
def list_recent_emails(max_results: int = 5) -> str:
    """
    List the sender and subject of the most recent inbox emails.

    Args:
        max_results: Maximum number of emails to return (default 5).
    """
    service = _get_gmail_service()

    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
        .execute()
    )

    messages = results.get("messages", [])

    if not messages:
        return "No recent emails found."

    lines = []
    for msg in messages:
        full = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"],
            )
            .execute()
        )

        headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        lines.append(
            f"From: {headers.get('From', 'Unknown')} | "
            f"Subject: {headers.get('Subject', '(no subject)')}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
