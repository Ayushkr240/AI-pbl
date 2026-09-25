"""
mcp_servers/calendar_server.py
-------------------------------
MCP server exposing Google Calendar actions as tools:
    - create_event
    - list_upcoming_events

This is the "Calendar Server (Google Calendar)" box in the architecture
diagram. Speaks MCP over stdio; launched as a subprocess by mcp_client.py.

One-time setup:
    1. In Google Cloud Console, enable the Google Calendar API on the
       same OAuth client used for Gmail (or a separate one).
    2. Reuse credentials.json from the email server setup, or point
       GOOGLE_CREDENTIALS_PATH at a different file.
    3. First run opens a browser to authorize; calendar_token.json is
       cached afterwards.

Env vars (optional overrides):
    GOOGLE_CREDENTIALS_PATH  (default: credentials.json)
    CALENDAR_TOKEN_PATH      (default: calendar_token.json)
"""

import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.getenv("CALENDAR_TOKEN_PATH", "calendar_token.json")

mcp = FastMCP("calendar-server")


def _get_calendar_service():
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

    return build("calendar", "v3", credentials=creds)


@mcp.tool()
def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    timezone: str = "Asia/Kolkata",
) -> str:
    """
    Create a Google Calendar event on the user's primary calendar.

    Args:
        summary: Event title.
        start_time: ISO 8601 start datetime, e.g. "2026-09-18T16:00:00".
        end_time: ISO 8601 end datetime, e.g. "2026-09-18T17:00:00".
        description: Optional event description.
        timezone: IANA timezone name (default "Asia/Kolkata").
    """
    service = _get_calendar_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }

    created = service.events().insert(calendarId="primary", body=event).execute()

    return f"Event '{summary}' created: {created.get('htmlLink')}"


@mcp.tool()
def list_upcoming_events(max_results: int = 5) -> str:
    """
    List the next upcoming events on the user's primary calendar.

    Args:
        max_results: Maximum number of events to return (default 5).
    """
    service = _get_calendar_service()

    now = datetime.datetime.utcnow().isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    if not events:
        return "No upcoming events found."

    lines = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        lines.append(f"{start} — {event.get('summary', '(no title)')}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
