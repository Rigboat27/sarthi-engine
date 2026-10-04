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


async def generate_with_fallback(body: dict, model: str | None = None) -> dict:
    """Try `model` first (if given), then the configured chain. Returns first success."""
    chain: list[str] = [model] if model else []
    chain += [m for m in config.GEMINI_MODELS if m != model]
    chain = [m for m in chain if m]
    if not chain:
        chain = ["gemini-3.5-flash-lite"]

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=90) as client:
        for m in chain:
            try:
                r = await client.post(_url(m), json=body)
                if r.status_code == 404 or r.status_code == 503:
                    last_error = RuntimeError(f"{m} -> {r.status_code}")
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:  # noqa: BLE001
                last_error = e
    raise last_error or RuntimeError("all Gemini models failed")


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
