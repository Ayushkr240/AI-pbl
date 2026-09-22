"""MCP server exposing Gmail actions as assistant tools."""

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
    credentials = None
    if os.path.exists(TOKEN_PATH):
        credentials = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(credentials.to_json())

    return build("gmail", "v1", credentials=credentials)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email through the user's Gmail account."""
    service = _get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to} (message id: {sent.get('id')})"


@mcp.tool()
def list_recent_emails(max_results: int = 5) -> str:
    """List sender and subject for recent inbox messages."""
    service = _get_gmail_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return "No recent emails found."

    lines = []
    for message in messages:
        full = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {header["name"]: header["value"] for header in full["payload"]["headers"]}
        lines.append(
            f"From: {headers.get('From', 'Unknown')} | "
            f"Subject: {headers.get('Subject', '(no subject)')}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
