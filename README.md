# 🤖 AI Voice Assistant & Productivity Copilot

A full-stack conversational AI assistant built with **Streamlit, LangGraph, Groq, RAG, SQLite, and MCP**.

The assistant can hold persistent multi-threaded conversations, answer questions from uploaded PDFs, accept **voice input**, and perform real-world productivity actions such as **sending emails and managing Google Calendar events** through MCP.

---

## ✨ Features

### 💬 Conversational AI

- Natural multi-turn conversations
- Persistent chat threads
- Create, rename, delete, and resume conversations
- Automatic conversation titles
- SQLite-backed conversation persistence

### 🎤 Voice Input

- Record voice directly from the Streamlit interface
- Speech-to-text using **Groq Whisper Large V3 Turbo**
- Voice input is converted into normal text input
- Voice and text follow the same chatbot workflow
- Fresh microphone instance after every recording
- Voice input works across different chat threads

### 📄 RAG — Retrieval Augmented Generation

- Upload PDF documents directly from the chat interface
- Extract and split document content
- Generate embeddings
- Store vectors using FAISS
- Retrieve relevant document context
- Generate answers grounded in uploaded documents

### 🧠 LangGraph Agent

The chatbot is orchestrated using LangGraph with:

- Input guardrails
- Document retrieval
- LLM reasoning
- MCP tool execution
- Output guardrails
- Persistent checkpointing

### 🔧 MCP Tool Integration

The assistant can interact with external services through the **Model Context Protocol (MCP)**.

#### 📧 Gmail MCP

- Read emails
- Search emails
- Send emails

#### 📅 Google Calendar MCP

- Read upcoming events
- Interact with Google Calendar
- Create calendar events where supported

### 🛡️ Guardrails

- Prompt-injection protection
- Unsafe-content filtering
- Input validation
- Output filtering
- PII protection
- Protection against leaking internal instructions

---

# 🏗️ Architecture

```text
                         ┌──────────────────────────────┐
                         │        Streamlit UI          │
                         │      frontend_sqlite.py      │
                         └──────────────┬───────────────┘
                                        │
                     ┌──────────────────┴──────────────────┐
                     │                                     │
                     ▼                                     ▼
                ⌨️ Text Input                         🎤 Voice Input
                     │                                     │
                     │                              Audio Recording
                     │                                     │
                     │                                     ▼
                     │                              Groq Whisper
                     │                           Large V3 Turbo STT
                     │                                     │
                     │                                     ▼
                     │                              Transcribed Text
                     │                                     │
                     └──────────────────┬──────────────────┘
                                        │
                                        ▼
                                  user_input
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │       LangGraph Agent        │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │  Input Guardrail  │
                              └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │   RAG Retrieval   │
                              └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │    Agent / LLM    │
                              └─────────┬─────────┘
                                        │
                              ┌─────────┴─────────┐
                              │                   │
                              ▼                   ▼
                       Normal Response       MCP Tool Call
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │                           │
                                    ▼                           ▼
                              Gmail MCP                 Calendar MCP
                                    │                           │
                                    ▼                           ▼
                               Gmail API                 Calendar API
                                    │                           │
                                    └─────────────┬─────────────┘
                                                  │
                                                  ▼
                                      ┌────────────────────┐
                                      │ Output Guardrail   │
                                      └──────────┬─────────┘
                                                 │
                                                 ▼
                                         Streamlit Response
```

---

# 🔄 Chatbot Workflow

```text
User
 │
 ├── Text
 │     │
 │     └──────────────────┐
 │                        │
 └── Voice                │
       │                  │
       ▼                  │
 Groq Whisper             │
       │                  │
       ▼                  │
 Transcribed Text ────────┘
              │
              ▼
        Input Guardrail
              │
              ▼
         RAG Retrieval
              │
              ▼
           Agent
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
   Normal LLM      MCP Tool
                     │
              ┌──────┴──────┐
              ▼             ▼
           Gmail         Calendar
              │             │
              └──────┬──────┘
                     ▼
              Output Guardrail
                     │
                     ▼
                  Response
```

---

# 🧩 LangGraph Architecture

The current LangGraph workflow consists of:

```text
START
  │
  ▼
guardrail_input
  │
  ▼
retrieve_node
  │
  ▼
agent_node
  │
  ├───────────────┐
  │               │
  │          Tool requested
  │               │
  │               ▼
  │           ToolNode
  │               │
  │               ▼
  │          agent_node
  │
  ▼
guardrail_output
  │
  ▼
 END
```

The graph uses asynchronous execution because the MCP tools and SQLite checkpointing require async-compatible execution.

---

# 🗄️ Persistence

The project uses SQLite for persistent state.

### LangGraph Checkpointing

```text
LangGraph
    │
    ▼
AsyncSqliteSaver
    │
    ▼
chatbot.db
```

This allows conversations to continue across application reruns.

### Thread Metadata

Thread information such as:

- Thread ID
- Chat title
- Rename state
- Deleted threads

is managed separately through `database.py`.

---

# 📚 RAG Pipeline

```text
PDF Upload
     │
     ▼
Document Loader
     │
     ▼
Text Splitting
     │
     ▼
Embeddings
     │
     ▼
FAISS Vector Store
     │
     ▼
Similarity Retrieval
     │
     ▼
Relevant Context
     │
     ▼
LangGraph Agent
     │
     ▼
Grounded Response
```

---

# 🎤 Voice Pipeline

Voice input is intentionally separated from the main chatbot workflow.

```text
Microphone
     │
     ▼
Streamlit Audio Input
     │
     ▼
Audio Bytes
     │
     ▼
backend_sqlite.py
     │
     ▼
Groq Whisper Large V3 Turbo
     │
     ▼
Text
     │
     ▼
Existing Chatbot Workflow
```

The microphone itself belongs to the frontend, while audio-to-text processing belongs to the backend.

After an audio recording is processed, the frontend creates a fresh microphone widget so the user can immediately make another recording.

---

# 🔧 MCP Architecture

```text
                    LangGraph Agent
                          │
                          ▼
                      ToolNode
                          │
                          ▼
                      MCP Client
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
        Gmail MCP                Calendar MCP
             │                         │
             ▼                         ▼
        Gmail API               Google Calendar API
```

MCP allows the assistant to interact with external services without tightly coupling those services to the LangGraph agent.

---

# 🛠️ Tech Stack

| Layer                  | Technology                   |
| ---------------------- | ---------------------------- |
| Frontend               | Streamlit                    |
| Programming Language   | Python 3.11                  |
| Agent Orchestration    | LangGraph                    |
| LLM Framework          | LangChain                    |
| LLM                    | Groq                         |
| Speech-to-Text         | Groq Whisper Large V3 Turbo  |
| RAG                    | LangChain + FAISS            |
| Embeddings             | Google Generative AI         |
| Vector Database        | FAISS                        |
| Conversation Memory    | SQLite                       |
| Async SQLite           | aiosqlite / AsyncSqliteSaver |
| External Tool Protocol | MCP                          |
| Email Integration      | Gmail API                    |
| Calendar Integration   | Google Calendar API          |
| Authentication         | Google OAuth                 |
| Environment Management | python-dotenv                |

---

# 📁 Project Structure

```text
AI-voice-assistant/
│
├── backend_sqlite.py          # LangGraph backend, LLM, STT and checkpointing
├── frontend_sqlite.py         # Streamlit UI, chat threads, PDF and voice input
├── database.py                # Chat thread metadata
├── guardrails.py              # Input/output safety and PII handling
│
├── mcp_client.py              # MCP client and tool loading
├── email_server.py            # Gmail MCP server
├── calender_server.py         # Google Calendar MCP server
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py          # Embedding and vectorstore operations
│   ├── loader.py              # PDF loading and text splitting
│   ├── prompts.py             # RAG / agent prompts
│   └── retriever.py           # Document retrieval
│
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Ignored files and secrets
│
└── .env                       # Local environment variables
```

> `.env`, OAuth credentials, tokens, databases, and other sensitive/generated files should not be committed to GitHub.

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone <your-repository-url>
cd AI-voice-assistant
```

## 2. Create a virtual environment

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

Important pinned versions include:

```text
streamlit==1.64.0
langchain-groq==1.1.3
groq==0.37.1
```

---

# 🔐 Environment Variables

Create a `.env` file in the project root.

Example:

```env
GROQ_API_KEY="your_groq_api_key"
GOOGLE_API_KEY="your_google_api_key"
```

For Gmail and Google Calendar MCP integration, configure the required Google OAuth credentials and tokens according to the MCP server configuration.

### Never commit

```text
.env
credentials.json
gmail_token.json
API keys
OAuth credentials
access tokens
```

---

# ▶️ Running the Application

Start the Streamlit application:

```bash
streamlit run frontend_sqlite.py
```

The application will open in your browser.

You can then:

- Create a chat
- Continue previous conversations
- Rename chats
- Delete chats
- Upload PDFs
- Ask questions about uploaded documents
- Use voice input
- Send emails through Gmail MCP
- Query Google Calendar
- Perform supported calendar actions

---

# 🧪 Example Prompts

### Normal Chat

```text
Explain what an API is.
```

### RAG

Upload a PDF and ask:

```text
Summarize chapter 3.
```

or:

```text
What are the main conclusions of this document?
```

### Voice

Record:

```text
What is the difference between TCP and UDP?
```

The voice is converted to text and then follows the normal chatbot workflow.

### Gmail MCP

```text
List my recent emails.
```

or:

```text
Send an email to my email address with subject "MCP Test"
and body "This is an MCP integration test."
```

### Calendar MCP

```text
What are my upcoming calendar events?
```

---

# 🛡️ Safety Features

The assistant includes multiple layers of protection:

- Prompt-injection detection
- Unsafe-content filtering
- Input validation
- Input length checks
- PII handling
- Output filtering
- Protection against exposing internal instructions
- Controlled MCP tool usage

The goal is to prevent the LLM from blindly executing external actions without appropriate user intent.

---

# ⚡ Important Async Architecture

The project uses asynchronous execution for MCP and SQLite checkpointing.

The chatbot is executed using:

```python
await chatbot.ainvoke(...)
```

through the asynchronous chatbot runner.

The project uses:

```python
AsyncSqliteSaver
```

instead of the synchronous:

```python
SqliteSaver
```

This is important because MCP tools are asynchronous.

Do not change this architecture to:

```python
chatbot.invoke(...)
```

or:

```python
SqliteSaver
```

without redesigning the corresponding execution flow.

---

# 🧠 Design Philosophy

The project is designed around a simple principle:

> **Different input methods should converge into the same chatbot workflow.**

Whether the user enters:

```text
⌨️ Text
```

or:

```text
🎤 Voice
```

the system eventually produces:

```python
user_input
```

and sends it through the same:

```text
Guardrails
    ↓
RAG
    ↓
LangGraph Agent
    ↓
MCP
    ↓
Response
```

This keeps the architecture modular and makes it easier to add future input methods.

---

# 🔮 Future Improvements

Potential future improvements include:

- True token-by-token response streaming
- Improved Streamlit UI/UX
- Better RAG retrieval and reranking
- Automated unit and integration tests
- More MCP integrations
- Confirmation workflows for sensitive actions
- Better MCP error handling
- Voice output / text-to-speech
- Improved deployment architecture
- More advanced conversation memory
- Production-grade authentication

---

# 📌 Current Status

The current working version includes:

- ✅ Streamlit chatbot
- ✅ LangGraph agent
- ✅ Groq LLM
- ✅ RAG with PDF uploads
- ✅ FAISS vector retrieval
- ✅ Persistent SQLite conversations
- ✅ Async SQLite checkpointing
- ✅ Chat threads
- ✅ Rename/delete chat
- ✅ Input/output guardrails
- ✅ Voice input
- ✅ Groq Whisper Large V3 Turbo STT
- ✅ Gmail MCP
- ✅ Google Calendar MCP
- ✅ Email sending through MCP
- ✅ Calendar interaction through MCP
- ✅ Multiple MCP tools in the same chatbot workflow

---

## 👨‍💻 Author

**Khushi Kumari , Ayush Kumar**

Built as an AI/ML project focused on combining conversational AI, RAG, agentic workflows, MCP integrations, and voice interaction into a single productivity assistant.
