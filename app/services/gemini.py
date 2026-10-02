"""Gemini conversation client (swappable for Sarvam-30b behind the same router)."""

import httpx

from app import config

_MODEL = "gemini-1.5-flash"


def mock_reply(messages: list) -> dict:
    """Zero-cost deterministic reply for MOCK_MODE."""
    last = (messages[-1]["content"] if messages else "").strip().lower()
    if last in ("", "hi", "hello", "namaste"):
        return {
            "reply": "Namaste! I'm Saathi. Tell me what happened in your own words.",
            "detectedLanguage": "hi",
        }
    return {
        "reply": "Got it. Can you tell me the name of the broker or company involved?",
        "detectedLanguage": "en",
    }


async def chat(messages: list, json_schema: dict | None = None) -> tuple[str, dict]:
    """Call Gemini generateContent and return (text, token_usage)."""
    url = f"{config.GEMINI_BASE}/models/{_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    contents = [
        {
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": m.get("content", "")}],
        }
        for m in messages
    ]
    body = {"contents": contents}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
        resp = r.json()

    parts = resp["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts)
    usage = resp.get("usageMetadata", {})
    return text, {
        "in": usage.get("promptTokenCount", 0),
        "out": usage.get("candidatesTokenCount", 0),
    }
