"""
prompts.py
----------

Builds the final prompt that will be sent to the LLM.

Responsibilities:
- Include conversation history
- Include retrieved document context
- Include the latest user question
"""

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
)

# ==========================================================
# System Prompt
# ==========================================================

SYSTEM_PROMPT = """
You are a helpful, accurate and professional AI assistant.

You have access to:

1. Previous Conversation History
2. Retrieved Document Context (if available)
3. The User's Latest Question

Instructions:

- Use the retrieved document context whenever it is relevant.
- If the retrieved context fully answers the question, prioritize it.
- If the retrieved context is incomplete, combine it with your own knowledge.
- Never claim information came from the uploaded documents unless it actually appears there.
- Never hallucinate facts supposedly contained in the documents.
- Answer naturally instead of copying large sections verbatim.
- Maintain conversation continuity using the previous messages.
- If the user asks a follow-up question, use the conversation history to understand the context.
- Keep responses clear, concise and well structured.
- If asked for code, produce complete, correct code.
"""

# ==========================================================
# Conversation Formatter
# ==========================================================


def format_messages(messages: list[BaseMessage]) -> str:
    """
    Convert LangChain messages into plain text conversation.
    """

    conversation = []

    for message in messages:

        if isinstance(message, HumanMessage):
            role = "User"

        elif isinstance(message, AIMessage):
            role = "Assistant"

        else:
            role = "System"

        conversation.append(f"{role}: {message.content}")

    return "\n".join(conversation)


# ==========================================================
# Prompt Builder
# ==========================================================


def build_prompt(
    messages: list[BaseMessage],
    context: str,
) -> str:
    """
    Build the complete prompt for the LLM.
    """

    conversation = format_messages(messages)

    if not context.strip():
        context = "No relevant document context was retrieved."

    prompt = f"""
{SYSTEM_PROMPT}

==================================================
Conversation History
==================================================

{conversation}

==================================================
Retrieved Document Context
==================================================

{context}

==================================================
Assistant
==================================================
"""

    return prompt.strip()