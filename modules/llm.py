import json
import os
import re
from typing import Any, Optional

from groq import Groq

import config


def get_client(api_key: Optional[str] = None) -> Groq:
    resolved_key = api_key or os.getenv("AI_API_KEY") or os.getenv("GROQ_API_KEY")
    if not resolved_key:
        raise ValueError("AI service is not configured. Add the API key in the .env file.")
    return Groq(api_key=resolved_key)


def ask_llm(messages: list[dict], api_key: Optional[str] = None, temperature: Optional[float] = None) -> str:
    client = get_client(api_key)
    response = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=messages,
        temperature=config.TEMPERATURE if temperature is None else temperature,
        max_tokens=config.MAX_TOKENS,
    )
    return response.choices[0].message.content or ""


def ask_groq(messages: list[dict], api_key: Optional[str] = None) -> str:
    return ask_llm(messages, api_key=api_key)


def extract_json_from_text(text: str) -> Any:
    fenced_match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("No JSON object found in model response.")
