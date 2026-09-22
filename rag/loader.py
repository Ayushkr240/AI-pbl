"""
loader.py
---------

Responsible for:
1. Loading PDF documents.
2. Splitting documents into chunks for RAG.

This module DOES NOT:
- Create embeddings
- Create vector stores
- Retrieve documents
- Interact with the LLM
"""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ==========================================================
# Configuration
# ==========================================================

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 250


# ==========================================================
# PDF Loader
# ==========================================================

def load_pdf(pdf_path: str) -> list[Document]:
    """
    Load a PDF file and return its pages as LangChain Document objects.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.

    Returns
    -------
    list[Document]
        A list of LangChain Document objects, one per page.

    Raises
    ------
    FileNotFoundError
        If the PDF file does not exist.
    """

    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_file}"
        )

    loader = PyPDFLoader(str(pdf_file))

    documents = loader.load()

    return documents


# ==========================================================
# Document Splitter
# ==========================================================

def split_documents(
    documents: list[Document],
) -> list[Document]:
    """
    Split documents into smaller overlapping chunks.

    Parameters
    ----------
    documents : list[Document]
        Documents returned by load_pdf().

    Returns
    -------
    list[Document]
        Chunked documents with metadata preserved.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_documents(documents)

    return chunks


# ==========================================================
# Combined Utility
# ==========================================================

def load_and_split_pdf(pdf_path: str) -> list[Document]:
    """
    Convenience function that loads a PDF and immediately
    returns chunked documents.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF.

    Returns
    -------
    list[Document]
        Chunked LangChain documents.
    """

    documents = load_pdf(pdf_path)

    chunks = split_documents(documents)

    return chunks