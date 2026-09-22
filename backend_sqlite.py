import asyncio
import sqlite3
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from guardrails import check_input, check_output
from mcp_client import get_mcp_tools
from rag.prompts import SYSTEM_PROMPT
from rag.retriever import format_context, retrieve_documents

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    streaming=True,
)

try:
    MCP_TOOLS = asyncio.run(get_mcp_tools())
except Exception as error:
    print(f"[mcp] Could not load MCP tools, continuing without them: {error}")
    MCP_TOOLS = []

llm_with_tools = llm.bind_tools(MCP_TOOLS) if MCP_TOOLS else llm


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context: str
    blocked: bool
    block_reason: str


def guardrail_input_node(state: ChatState, config: RunnableConfig) -> ChatState:
    thread_id = config["configurable"]["thread_id"]
    last_message = state["messages"][-1]
    result = check_input(thread_id, last_message.content)

    if not result.allowed:
        return {"blocked": True, "block_reason": result.reason}

    last_message.content = result.sanitized_text
    return {"blocked": False, "block_reason": ""}


def retrieve_node(state: ChatState, config: RunnableConfig) -> ChatState:
    if state.get("blocked"):
        return {"context": ""}

    thread_id = config["configurable"]["thread_id"]
    query = state["messages"][-1].content

    try:
        documents = retrieve_documents(thread_id=thread_id, query=query)
        context = format_context(documents)
    except Exception:
        context = ""

    return {"context": context}


def agent_node(state: ChatState) -> ChatState:
    if state.get("blocked"):
        reason = state.get("block_reason", "This request was blocked by guardrails.")
        return {"messages": [AIMessage(content=f"I can't help with that: {reason}")]}

    system = SystemMessage(
        content=(
            f"{SYSTEM_PROMPT}\n\n"
            "You also have tools available to send emails and manage Google "
            "Calendar events. Use a tool only when the user's request clearly "
            "asks for one of those actions.\n\n"
            "Retrieved Document Context\n\n"
            f"{state.get('context') or 'No relevant document context was retrieved.'}"
        )
    )
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}


def guardrail_output_node(state: ChatState) -> ChatState:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not isinstance(last_message.content, str):
        return {}

    result = check_output(last_message.content)
    last_message.content = result.sanitized_text if result.allowed else result.reason
    return {}


def generate_chat_title(first_message: str) -> str:
    prompt = f"""
You are an AI that creates very short conversation titles.
Rules:
- Maximum 2 or 3 words.
- No punctuation, quotation marks, emojis.
- Return ONLY the title.

User Message:
{first_message}
"""

    try:
        response = llm.invoke(prompt)
        title = response.content.strip().replace('"', "").replace("'", "")
        title = " ".join(title.split()[:3])
        return title or "New Chat"
    except Exception:
        return "New Chat"


conn = sqlite3.connect("chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("guardrail_input", guardrail_input_node)
graph.add_node("retrieve_node", retrieve_node)
graph.add_node("agent_node", agent_node)
graph.add_node("guardrail_output", guardrail_output_node)
graph.add_edge(START, "guardrail_input")
graph.add_edge("guardrail_input", "retrieve_node")
graph.add_edge("retrieve_node", "agent_node")

if MCP_TOOLS:
    graph.add_node("tools", ToolNode(MCP_TOOLS))
    graph.add_conditional_edges(
        "agent_node", tools_condition, {"tools": "tools", END: "guardrail_output"}
    )
    graph.add_edge("tools", "agent_node")
else:
    graph.add_edge("agent_node", "guardrail_output")

graph.add_edge("guardrail_output", END)
chatbot = graph.compile(checkpointer=checkpointer)
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
