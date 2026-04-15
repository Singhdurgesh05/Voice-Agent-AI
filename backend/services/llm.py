"""
Groq LLM service with tool-calling support.

Sends user messages to the Groq API along with tool definitions so the
model can decide which local tools to invoke (create_file, create_folder, write_code,
summarize_text) or simply respond as a general chatbot.
"""

import json
from groq import Groq
from backend.config import settings


# ── Tool Definitions (OpenAI-compatible function calling) ────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": (
                "Create a new empty file in the output directory. "
                "Use this when the user wants to create a blank file without specific code content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to create (e.g. 'notes.txt', 'data.json').",
                    },
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": (
                "Create a folder in the output directory. "
                "Use this when the user asks to create a directory/folder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "foldername": {
                        "type": "string",
                        "description": "Folder name/path to create under output (e.g. 'src', 'python/utils').",
                    },
                },
                "required": ["foldername"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_code",
            "description": (
                "Generate code based on the user's request and write it to a file. "
                "Use this when the user wants to create a file with code or asks you to write code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename to save the code to (e.g. 'retry.py', 'utils.js').",
                    },
                    "code": {
                        "type": "string",
                        "description": "The complete code content to write to the file.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (e.g. 'python', 'javascript').",
                    },
                },
                "required": ["filename", "code", "language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": (
                "Summarize provided text content. "
                "Use this when the user asks to summarize or condense information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text content to summarize.",
                    },
                },
                "required": ["text"],
            },
        },
    },
]


# ── System Prompt ────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an intelligent voice-controlled AI agent called **Voice Agent**.
Your job is to understand the user's intent from their transcribed speech and
execute the appropriate tools.

Available tools:
• **create_file** – Create a new empty file.
• **create_folder** – Create a new folder.
• **write_code**  – Generate high-quality code and save it to a file.
• **summarize_text** – Summarize provided text.

Guidelines:
1. If the user asks to create a file **with** code, use `write_code`.
2. If the user asks to create a file **without** specific content, use `create_file`.
3. If the user asks to create a folder/directory, use `create_folder`.
4. If the user asks to summarize something, use `summarize_text`.
5. For general conversation, respond directly **without** calling any tool.
6. You MAY call **multiple tools** in a single response for compound commands
   (e.g. "Create a Python retry function and save it, then summarize what it does.").
7. Always generate well-structured, well-commented code when using `write_code`.
8. Keep all generated files/folders under the output sandbox.
9. Be helpful, concise, and friendly.
"""


# ── LLM Service ─────────────────────────────────────────────────

class LLMService:
    """Wrapper around the Groq chat completions API with tool support."""

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    async def process(
        self,
        user_message: str,
        context: list[dict] | None = None,
        memory_context: str | None = None,
    ) -> dict:
        """
        Send a user message to Groq and return parsed intent + tool calls.

        Returns
        -------
        dict with keys:
            response_text : str          – LLM's text reply
            tool_calls    : list[dict]   – extracted tool invocations
            intent        : str          – dominant intent label
        """
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if memory_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant context from previous conversations:\n"
                        + memory_context
                    ),
                }
            )

        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=4096,
        )

        choice = response.choices[0]

        result = {
            "response_text": choice.message.content or "",
            "tool_calls": [],
            "intent": "general_chat",
        }

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                result["tool_calls"].append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments),
                    }
                )

            # Determine the dominant intent from the tool calls
            tool_names = [tc["name"] for tc in result["tool_calls"]]
            if "write_code" in tool_names:
                result["intent"] = "write_code"
            elif "create_folder" in tool_names:
                result["intent"] = "create_folder"
            elif "create_file" in tool_names:
                result["intent"] = "create_file"
            elif "summarize_text" in tool_names:
                result["intent"] = "summarize_text"

        return result


llm_service = LLMService()
