"""
retriever.py
------------

Responsible for:
1. Loading a thread's FAISS vector store.
2. Retrieving the most relevant documents.
3. Formatting retrieved documents into context for the LLM.

This module does NOT:
- Load PDFs
- Create embeddings
- Communicate with the LLM
"""

from langchain_core.documents import Document

from rag.embeddings import load_vectorstore


# ==========================================================
# Configuration
# ==========================================================

TOP_K = 4


# ==========================================================
# Retrieve Documents
# ==========================================================

def retrieve_documents(
    thread_id: str,
    query: str,
    k: int = TOP_K,
) -> list[Document]:
    """
    Retrieve the most relevant documents for a user query.

    Args:
        thread_id: Thread ID whose vector store should be searched.
        query: User's question.
        k: Number of documents to retrieve.

    Returns:
        List of LangChain Document objects.
    """

    vectorstore = load_vectorstore(thread_id)

    results = vectorstore.similarity_search_with_score(
        query=query,
        k=k,
    )

    documents: list[Document] = []

    for document, score in results:
        document.metadata["score"] = round(float(score), 3)
        documents.append(document)

    return documents


# ==========================================================
# Format Context
# ==========================================================

def format_context(documents: list[Document]) -> str:
    """
    Convert retrieved documents into a formatted context string
    for the LLM.

    Args:
        documents: Retrieved LangChain Documents.

    Returns:
        A formatted string containing the retrieved context.
    """

    if not documents:
        return "No relevant context found."

    context_parts = []

    for index, doc in enumerate(documents, start=1):

        source = doc.metadata.get("source", "Unknown")

        # Prefer page_label if available (1-based page number)
        page = doc.metadata.get(
            "page_label",
            doc.metadata.get("page", "Unknown")
        )

        section = (
            f"Document {index}\n"
            f"Source: {source}\n"
            f"Page: {page}\n\n"
            f"{doc.page_content.strip()}"
        )

        context_parts.append(section)

    separator = "\n\n" + ("-" * 80) + "\n\n"

    return separator.join(context_parts)