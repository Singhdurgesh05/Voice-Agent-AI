"""
Text-processing tools.

Uses the Groq LLM to perform summarisation so the quality
matches the main agent's language capabilities.
"""

from groq import Groq
from backend.config import settings


def summarize_text(text: str) -> dict:
    """Return a concise summary of *text* using Groq."""
    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise text summariser. "
                    "Provide a clear, well-structured summary in 2–3 paragraphs maximum."
                ),
            },
            {
                "role": "user",
                "content": f"Please summarise the following text:\n\n{text}",
            },
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    summary = response.choices[0].message.content

    return {
        "success": True,
        "message": "Text summarised successfully.",
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
    }
