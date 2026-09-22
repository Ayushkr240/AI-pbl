"""
embeddings.py
-------------

Responsible for:
1. Creating the Google embedding model.
2. Creating FAISS vector stores.
3. Saving vector stores.
4. Loading vector stores.
5. Updating existing vector stores.

This module DOES NOT:
- Load PDFs
- Retrieve documents
- Interact with the LLM
"""

from pathlib import Path

from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()


# ==========================================================
# Configuration
# ==========================================================

EMBEDDING_MODEL = "models/gemini-embedding-001"

VECTORSTORE_ROOT = Path("vectorstores")


# ==========================================================
# Embedding Model
# ==========================================================

def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """
    Create and return the Google embedding model.
    """

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        task_type="retrieval_document"
    )


# ==========================================================
# Vector Store Path
# ==========================================================

def get_vectorstore_path(thread_id: str) -> Path:
    """
    Returns the directory where the thread's
    vector store is stored.
    """

    return VECTORSTORE_ROOT / thread_id


# ==========================================================
# Check if Vector Store Exists
# ==========================================================

def vectorstore_exists(thread_id: str) -> bool:
    """
    Returns True if a FAISS vector store already exists
    for the given thread.
    """

    vectorstore_path = get_vectorstore_path(thread_id)

    return (
        (vectorstore_path / "index.faiss").exists()
        and
        (vectorstore_path / "index.pkl").exists()
    )


# ==========================================================
# Create Vector Store
# ==========================================================

def create_vectorstore(
    documents: list[Document],
) -> FAISS:
    """
    Create a FAISS vector store from documents.
    """

    embedding_model = get_embedding_model()

    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model
    )

    return vectorstore


# ==========================================================
# Save Vector Store
# ==========================================================

def save_vectorstore(
    vectorstore: FAISS,
    thread_id: str,
) -> None:
    """
    Save a FAISS vector store to disk.
    """

    vectorstore_path = get_vectorstore_path(thread_id)

    vectorstore_path.mkdir(
        parents=True,
        exist_ok=True
    )

    vectorstore.save_local(
        folder_path=str(vectorstore_path)
    )


# ==========================================================
# Load Vector Store
# ==========================================================

def load_vectorstore(
    thread_id: str,
) -> FAISS:
    """
    Load an existing FAISS vector store.
    """

    if not vectorstore_exists(thread_id):
        raise FileNotFoundError(
            f"No vector store found for thread '{thread_id}'"
        )

    embedding_model = get_embedding_model()

    vectorstore = FAISS.load_local(
        folder_path=str(get_vectorstore_path(thread_id)),
        embeddings=embedding_model,
        allow_dangerous_deserialization=True,
    )

    return vectorstore


# ==========================================================
# Add Documents
# ==========================================================

def add_documents(
    thread_id: str,
    documents: list[Document],
) -> None:
    """
    Load an existing vector store,
    add documents,
    and save it back to disk.
    """

    vectorstore = load_vectorstore(thread_id)

    vectorstore.add_documents(documents)

    save_vectorstore(
        vectorstore,
        thread_id,
    )