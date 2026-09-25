# ==================== 1. IMPORTS ====================

import asyncio
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
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

# ==================== 2. ENVIRONMENT & MODEL / MCP SETUP ====================

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


# ==================== 3. CHAT STATE ====================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context: str
    blocked: bool
    block_reason: str


# ==================== 4. INPUT GUARDRAIL ====================

def guardrail_input_node(state: ChatState, config: RunnableConfig) -> ChatState:
    thread_id = config["configurable"]["thread_id"]
    last_message = state["messages"][-1]
    result = check_input(thread_id, last_message.content)

    if not result.allowed:
        return {"blocked": True, "block_reason": result.reason}

    last_message.content = result.sanitized_text
    return {"blocked": False, "block_reason": ""}


# ==================== 5. RAG RETRIEVAL ====================

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


# ==================== 6. AGENT NODE ====================

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


# ==================== 7. OUTPUT GUARDRAIL ====================

def guardrail_output_node(state: ChatState) -> ChatState:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not isinstance(last_message.content, str):
        return {}

    result = check_output(last_message.content)
    last_message.content = result.sanitized_text if result.allowed else result.reason
    return {}


# ==================== 8. CHAT TITLE GENERATION ====================

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


# ==================== 9. DATABASE & CHECKPOINTER ====================

# async def get_checkpointer():
#     conn = await aiosqlite.connect("chatbot.db")
#     return AsyncSqliteSaver(conn)

# checkpointer = asyncio.run(get_checkpointer())

# ==================== 10. LANGGRAPH GRAPH ====================

def create_graph(checkpointer):
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
            "agent_node",
            tools_condition,
            {"tools": "tools", END: "guardrail_output"},
        )
        graph.add_edge("tools", "agent_node")
    else:
        graph.add_edge("agent_node", "guardrail_output")

    graph.add_edge("guardrail_output", END)

    return graph.compile(checkpointer=checkpointer)

# ==================== 11. ASYNC CHATBOT RUNNER ====================

async def run_chatbot(input_data, config):
    async with AsyncSqliteSaver.from_conn_string("chatbot.db") as checkpointer:
        chatbot = create_graph(checkpointer)

        result = await chatbot.ainvoke(
            input_data,
            config=config,
        )

        return result