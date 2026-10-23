"""Connection to the AI model, plus a helper that reliably gets structured data back.

We use the OpenAI Python library pointed at Ollama. To switch to OpenAI later,
change LLM_BASE_URL and LLM_MODEL in .env; nothing else needs to change.
"""

import json
import os
import re
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()

# Default: your Mac's Ollama app, which forwards gemma4:cloud to Ollama's servers.
BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("LLM_MODEL", "gemma4:cloud")
API_KEY = os.getenv("LLM_API_KEY", "ollama")  # the local Ollama server ignores this

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

T = TypeVar("T", bound=BaseModel)


def chat(messages: list[dict]) -> str:
    """Send a conversation to the model and return its text reply."""
    reply = client.chat.completions.create(model=MODEL, messages=messages)
    return reply.choices[0].message.content or ""


def _extract_json(text: str) -> str:
    """Gemma often wraps JSON in ```json fences. Pull out just the JSON part."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    return text[start:].strip() if start != -1 else text.strip()


def ask_json(messages: list[dict], schema: type[T], retries: int = 1) -> T:
    """Ask the model for data matching `schema` (a Pydantic model).

    If the reply is broken or has the wrong shape, we tell the model what went
    wrong and ask again, up to `retries` extra times.
    """
    instructions = (
        "Reply with only a JSON object matching this JSON Schema, and no other text:\n"
        + json.dumps(schema.model_json_schema())
    )
    convo = [{"role": "system", "content": instructions}, *messages]

    for attempt in range(retries + 1):
        text = chat(convo)
        try:
            return schema.model_validate_json(_extract_json(text))
        except ValidationError as err:
            if attempt == retries:
                raise
            convo += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"That JSON was invalid: {err}. Reply again with only valid JSON."},
            ]
    raise RuntimeError("unreachable")
