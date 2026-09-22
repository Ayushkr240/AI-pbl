# AI Voice Assistant & Productivity Copilot

This project is a personal AI assistant designed to combine conversational intelligence with practical productivity actions. It goes beyond a simple chatbot: it can answer questions from uploaded documents, maintain long-running threaded conversations, and act on external tools such as Gmail and Google Calendar through the Model Context Protocol (MCP). The system is built around a LangGraph agent, a retrieval-augmented generation (RAG) pipeline, persistent SQLite memory, and safety guardrails to keep responses reliable and user-safe.

---

## Project vision

The goal of this project is to create an AI assistant that feels more like a real digital productivity companion than a static Q&A bot. In practice, that means the assistant can:

- chat naturally in a multi-threaded interface
- answer questions grounded in uploaded PDFs and knowledge documents
- remember previous conversations within a thread
- decide when to use external tools such as email or calendar actions
- block unsafe or manipulative requests before they affect model behavior
- provide a foundation that can later evolve into a voice-first assistant experience

This is why the system is designed as a full agentic workflow rather than only a document chatbot.

---

## Core capabilities

- Conversational AI with multi-thread chat history
- Persistent memory using SQLite checkpoints
- PDF upload and knowledge retrieval using FAISS + embeddings
- Retrieval-augmented generation for grounded responses
- Tool-calling via MCP for Gmail and Google Calendar
- Input/output guardrails for prompt injection, unsafe content, and PII handling
- Streamlit-based desktop-style frontend for local interaction
- Automatic conversation titles for easier organization

---

## Architecture overview

```text
                         ┌────────────────────────────┐
                         │        Streamlit UI       │
                         │      Frontend App         │
                         └──────────────┬─────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │       LangGraph Agent      │
                         │  Guardrails + Retrieval    │
                         │       + LLM orchestration  │
                         └──────────────┬─────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
            ▼                           ▼                           ▼
┌────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ SQLite Memory      │     │ RAG Layer            │     │ MCP Tool Servers      │
│ Thread state       │     │ FAISS + embeddings   │     │ Gmail / Calendar      │
│ Conversation logs  │     │ PDF chunk search     │     │ external actions      │
└────────────────────┘     └──────────────────────┘     └──────────────────────┘
            │                           │                           │
            └───────────────────────────┴───────────────────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │      LLM Response          │
                         │  (Groq / model provider)  │
                         └────────────────────────────┘
```

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Application UI | Streamlit |
| Agent orchestration | LangGraph |
| LLM integration | LangChain + Groq / model provider |
| Embeddings | Google Generative AI embeddings |
| Vector search | FAISS |
| Memory | SQLite |
| Knowledge retrieval | RAG pipeline |
| External tools | MCP (Model Context Protocol) |
| Google integrations | Gmail API, Google Calendar API |
| Safety | custom rule-based guardrails |
| Runtime | Python |

---

## Repository structure

```text
.
├── backend_sqlite.py          # LangGraph chatbot logic and memory orchestration
├── frontend_sqlite.py         # Streamlit interface and chat/thread management
├── database.py                # SQLite thread metadata storage
├── guardrails.py              # Input/output filtering and PII safeguards
├── calendar_server.py         # Google Calendar MCP server
├── mcp_client.py              # Client that connects to MCP tool servers
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview and setup guide
├── SETUP_PHASE1.md            # Setup notes for initial project phase
├── rag/                       # Retrieval and document-processing components
│   ├── __init__.py
│   ├── embeddings.py
│   ├── loader.py
│   ├── prompts.py
│   ├── retriever.py
│   └── ...
├── .gitignore
└── .env.example (optional)   # if you add a local env template
```

---

## How it works

1. The user opens the Streamlit app and starts or resumes a chat thread.
2. The assistant checks the latest user message through guardrails.
3. If the query is relevant to uploaded documents, the app retrieves matching chunks from the FAISS vector store.
4. The LangGraph workflow combines:
   - conversation history
   - retrieved context
   - the latest user message
5. The model generates the response using that combined context.
6. If the user asks to send email or manage calendar tasks, the agent may invoke MCP tools connected to Google services.
7. All thread data and conversation state are stored in SQLite for continuity across sessions.

---

## Getting started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Ai-Assistant-Chatbot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root with the keys required by the LLM and Google integrations.

```env
GOOGLE_API_KEY="your_google_api_key"
GROQ_API_KEY="your_groq_api_key"
```

If you want to enable the Gmail and Calendar tool integrations, also prepare the Google OAuth credentials for the project and ensure the relevant Google Cloud APIs are enabled.

---

## Running the app

Start the Streamlit app:

```bash
streamlit run frontend_sqlite.py
```

Once the app is running, you can:

- create a new chat thread
- upload a PDF for knowledge retrieval
- ask questions grounded in the uploaded material
- use the assistant in a threaded conversation
- trigger external actions when appropriate via MCP-backed tools

---

## Safety and trust features

The assistant is intentionally designed with safeguards so it is not just a raw model wrapper:

- prompt-injection detection
- blocked-topic filtering
- input length and rate-limit checks
- PII redaction in user input/output
- output-side leak prevention for internal instructions
- tool use restricted to clear user intent

This matters because the app is intended to operate as a personal assistant with real-world actions, not just a passive chat interface.

---

## Why this project matters

This repository represents a practical blueprint for an AI-powered personal assistant that can:

- understand ongoing conversations
- ground answers in user documents
- operate securely in a bounded tool environment
- connect to real productivity workflows like email and scheduling

It is a strong starting point for a voice-enabled AI productivity assistant, a document-aware copilot, or a personal knowledge assistant.

---

## Future direction

The project is already structured for expansion toward a richer assistant experience, including:

- voice input and spoken responses
- source citations for document-grounded answers
- smarter multi-document knowledge management
- agent personalization and memory improvements
- more productivity tools beyond email and calendar
- better orchestration for complex task workflows

---

## Contributing

Contributions are welcome. If you want to improve the assistant, add features, or extend the tool layer, open a pull request with a clear summary and relevant testing.

---

## License

This project is provided for learning and personal use. Add your preferred license if you plan to distribute or publish it more broadly.

---

## Author

Ayush Kumar

GitHub: https://github.com/Ayushkr240
