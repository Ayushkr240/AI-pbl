import uuid
import asyncio
import asyncio
import hashlib
from groq import Groq
from backend_sqlite import create_graph, generate_chat_title, run_chatbot , transcribe_audio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from rag.embeddings import save_vectorstore
from database import (
    create_thread,
    get_all_threads,
    rename_thread,
    delete_thread,
)

import os
import tempfile

from rag.loader import load_and_split_pdf
from rag.embeddings import (
    vectorstore_exists,
    create_vectorstore,
    add_documents,
)
# ============================================================
# Utility Functions
# ============================================================

def generate_thread_id():
    return str(uuid.uuid4())

def add_thread(thread_id, title="New Chat"):
    """Add a thread to the database if it doesn't already exist."""

    create_thread(thread_id, title)

    st.session_state["chat_threads"] = get_all_threads()


def reset_chat():
    """Start a brand-new conversation."""

    new_thread = generate_thread_id()

    st.session_state["thread_id"] = new_thread
    st.session_state["message_history"] = []

    add_thread(new_thread)


async def load_conversation(thread_id):
    """Load conversation from LangGraph checkpointer."""

    async with AsyncSqliteSaver.from_conn_string("chatbot.db") as checkpointer:
        chatbot = create_graph(checkpointer)

        state = await chatbot.aget_state(
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            }
        )

        return state.values.get("messages", [])


# ============================================================
# Session State Initialization
# ============================================================


if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = get_all_threads()

add_thread(st.session_state["thread_id"])

if "uploaded_pdf" not in st.session_state:
    st.session_state["uploaded_pdf"] = None
    
if "attachment_key" not in st.session_state:
    st.session_state["attachment_key"] = 0

if "voice_input_key" not in st.session_state:
    st.session_state["voice_input_key"] = 0
# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("🤖 LangGraph Chatbot")


if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

    
st.sidebar.divider()
st.sidebar.subheader("My Conversations")


for thread in st.session_state["chat_threads"]:

    col1, col2 = st.sidebar.columns([9, 2])

    # ---------------------------
    # Chat Button
    # ---------------------------
    with col1:

        if st.button(
            thread["title"],
            key=f"chat_{thread['id']}",
            use_container_width=True,
        ):

            st.session_state["thread_id"] = thread["id"]

            messages = asyncio.run(load_conversation(thread["id"]))

            history = []

            for msg in messages:

                role = "user" if isinstance(msg, HumanMessage) else "assistant"

                history.append(
                    {
                        "role": role,
                        "content": msg.content,
                    }
                )

            st.session_state["message_history"] = history

            st.rerun()

    # ---------------------------
    # Popover Menu
    # ---------------------------
    with col2:

        with st.popover("⋮", use_container_width=True):

            st.markdown(f"**{thread['title']}**")

            st.divider()

            # -------------------
            # Rename
            # -------------------

            new_name = st.text_input(
                "Rename",
                value=thread["title"],
                key=f"rename_input_{thread['id']}",
            )

            if st.button(
                "💾 Save",
                key=f"save_{thread['id']}",
                use_container_width=True,
            ):
                new_title = new_name.strip() or "New Chat"

                rename_thread(
                    thread["id"],
                    new_title,
                )

                st.session_state["chat_threads"] = get_all_threads()

                st.rerun()

            # -------------------
            # Delete
            # -------------------

            if st.button(
                "🗑️ Delete Chat",
                key=f"delete_{thread['id']}",
                type="primary",
                use_container_width=True,
            ):
                delete_thread(thread["id"])
                deleted_current = (
                    thread["id"] == st.session_state["thread_id"]
                )

                st.session_state["chat_threads"] = get_all_threads()

                if deleted_current:

                    if st.session_state["chat_threads"]:

                        latest = st.session_state["chat_threads"][-1]

                        st.session_state["thread_id"] = latest["id"]

                        messages = load_conversation(latest["id"])

                        history = []

                        for msg in messages:

                            role = (
                                "user"
                                if isinstance(msg, HumanMessage)
                                else "assistant"
                            )

                            history.append(
                                {
                                    "role": role,
                                    "content": msg.content,
                                }
                            )

                        st.session_state["message_history"] = history

                    else:

                        reset_chat()

                st.rerun()

# ============================================================
# Chat History
# ============================================================

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================================
# User Input
# ============================================================

user_input = None
chat_data = None
voice_data = None


# ============================================================
# Bottom Input Area
# ============================================================

with st.bottom:

    # -------------------------
    # Text Input
    # -------------------------

    chat_data = st.chat_input(
        "Type here...",
        accept_file=True,
        file_type=["pdf"],
    )

    # -------------------------
    # Voice Input
    # -------------------------

    voice_data = st.audio_input(
        "🎤 Record your voice",
        key=f"voice_input_{st.session_state['voice_input_key']}"
    )


# ============================================================
# Handle Voice Input
# ============================================================

if voice_data is not None:

    with st.spinner("Converting speech to text..."):

        user_input = transcribe_audio(
            voice_data.getvalue()
        )

    # Force a fresh microphone widget
    st.session_state["voice_input_key"] += 1


# ============================================================
# Handle Text Input
# ============================================================

if user_input is None and chat_data is not None:

    user_input = chat_data.text

    if chat_data.files:
        st.session_state["uploaded_pdf"] = chat_data.files[0]

if user_input:

    # -------------------------
    # User Message
    # -------------------------

    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # -------------------------
    # Generate title ONLY once
    # -------------------------

    if len(st.session_state["message_history"]) == 1:

        title = generate_chat_title(user_input)

        rename_thread(
            st.session_state["thread_id"],
            title,
        )

        st.session_state["chat_threads"] = get_all_threads()


    # --------------------------------------------------
    # Process Attached PDF
    # --------------------------------------------------

    if st.session_state["uploaded_pdf"] is not None:

        with tempfile.NamedTemporaryFile(
            delete=False,
        suffix=".pdf",
        ) as tmp:

            tmp.write(
                st.session_state["uploaded_pdf"].read()
            )

            pdf_path = tmp.name

        with st.spinner("Processing PDF..."):

            documents = load_and_split_pdf(pdf_path)

            thread_id = st.session_state["thread_id"]

            if vectorstore_exists(thread_id):

                add_documents(
                    thread_id=thread_id,
                    documents=documents,
                )

            else:

                vectorstore = create_vectorstore(documents)

                save_vectorstore(
                    vectorstore=vectorstore,
                    thread_id=thread_id,
                )

        os.remove(pdf_path)
    

    # Clear uploaded PDF after successful indexing
    st.session_state["uploaded_pdf"] = None
    st.session_state["attachment_key"] += 1
    # -------------------------
    # LangGraph Config
    # -------------------------

    CONFIG = {
        "configurable": {
            "thread_id": st.session_state["thread_id"]
        }
    }

    # -------------------------
    # AI Response Streaming
    # -------------------------

    with st.chat_message("assistant"):

        result = asyncio.run(
            run_chatbot(
                {
                    "messages": [
                        HumanMessage(content=user_input)
                    ]
                },
                config=CONFIG,
            )
        )

        ai_response = result["messages"][-1].content

        st.markdown(ai_response)

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": ai_response,
        }
    )
    st.rerun()