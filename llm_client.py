"""
OpenRouter LLM Client for PSX Investment Agents.

Reads API key and model from the local SQLite database (same DB used by the
Next.js app via Prisma). Calls the OpenRouter API using only Python stdlib
modules — no extra packages required.

Usage:
    from llm_client import chat_completion

    # Simple query
    reply = chat_completion(
        messages=[{"role": "user", "content": "Summarize PSX market conditions."}],
        system_prompt="You are an expert investment analyst for PSX stocks."
    )
    print(reply)

    # Override model per-call
    reply = chat_completion(
        messages=[{"role": "user", "content": "Analyze OGDC fundamentals."}],
        model="anthropic/claude-sonnet-4-5"
    )
"""

import json
import os
import sqlite3
import urllib.error
import urllib.request
from typing import Optional

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Path to the Prisma SQLite database relative to this file
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prisma", "dev.db")


def _get_settings() -> dict:
    """
    Read LlmSettings from the SQLite database.

    Returns:
        dict with keys "apiKey" and "model"

    Raises:
        RuntimeError: If no settings row exists or API key is empty.
    """
    if not os.path.exists(_DB_PATH):
        raise RuntimeError(
            f"Database not found at {_DB_PATH}. "
            "Run 'npx prisma migrate dev' from the project root first."
        )

    conn = sqlite3.connect(_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT apiKey, model FROM LlmSettings LIMIT 1")
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row or not row[0]:
        raise RuntimeError(
            "OpenRouter API key not configured. "
            "Open the Next.js app at /llm, enter your API key in Settings, and save."
        )

    return {"apiKey": row[0], "model": row[1]}


def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Send a chat request to OpenRouter and return the assistant's reply.

    Args:
        messages: List of message dicts with "role" and "content" keys.
                  Roles: "user", "assistant", or "system".
        model: OpenRouter model ID to use. Defaults to the model saved in the DB.
               Example: "openai/gpt-4o-mini", "anthropic/claude-sonnet-4-5"
        system_prompt: Optional system instruction prepended to the messages list.
        temperature: Sampling temperature (0.0–2.0). Default 0.7.
        max_tokens: Maximum tokens to generate. None means model default.

    Returns:
        str: The assistant's reply text.

    Raises:
        RuntimeError: If the API key is not configured or the request fails.
    """
    settings = _get_settings()
    resolved_model = model or settings["model"]

    # Build the messages list, optionally prepending a system message
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    payload: dict = {
        "model": resolved_model,
        "messages": all_messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {settings['apiKey']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PSX Investment Assistant",
    }

    request_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{OPENROUTER_BASE_URL}/chat/completions",
        data=request_data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(
            f"OpenRouter API error {e.code}: {error_body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling OpenRouter: {e.reason}") from e

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected OpenRouter response format: {body}") from e


# ---------------------------------------------------------------------------
# Example usage when run as a script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing OpenRouter LLM client...")
    try:
        settings = _get_settings()
        print(f"Using model: {settings['model']}")
        reply = chat_completion(
            messages=[{"role": "user", "content": "Say hello and confirm you are working."}],
            system_prompt="You are a helpful AI assistant for PSX investment analysis.",
        )
        print(f"\nAssistant: {reply}")
    except RuntimeError as e:
        print(f"\nError: {e}")
