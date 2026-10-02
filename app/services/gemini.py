"""Gemini client shared by the proxy passthrough and the /docs domain endpoints."""

import httpx

from app import config


def _url(model: str) -> str:
    return f"{config.GEMINI_BASE}/models/{model}:generateContent?key={config.GEMINI_API_KEY}"


async def generate(model: str, body: dict) -> dict:
    """POST to Gemini generateContent and return the parsed JSON response."""
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(_url(model), json=body)
        r.raise_for_status()
        return r.json()


def extract_text(resp: dict) -> str:
    """Pull the concatenated text out of a Gemini generateContent response."""
    try:
        return "".join(
            p.get("text", "") for p in resp["candidates"][0]["content"]["parts"]
        )
    except (KeyError, IndexError, TypeError):
        return ""


def inline_image(data_url: str) -> dict:
    """Split a data URL (or raw base64) into a Gemini inlineData part."""
    if data_url.startswith("data:"):
        header, _, b64 = data_url.partition(",")
        mime = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
        return {"inlineData": {"mimeType": mime, "data": b64}}
    return {"inlineData": {"mimeType": "image/jpeg", "data": data_url}}
