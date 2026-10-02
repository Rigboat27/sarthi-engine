"""Sarvam speech client (Saaras v4 STT, Bulbul v3 TTS).

Endpoints verified against docs.sarvam.ai (Oct 2026). Auth is the
`api-subscription-key` header; a 403 means an auth failure.
"""

import httpx

from app import config

# Deterministic counter so mock STT is stable across a demo (zero spend).
_tick = 0


def mock_tick() -> int:
    global _tick
    _tick += 1
    return _tick


async def transcribe(audio: bytes, filename: str) -> dict:
    """POST /speech-to-text (multipart), model saaras:v4."""
    url = f"{config.SARVAM_BASE}/speech-to-text"
    headers = {"api-subscription-key": config.SARVAM_API_KEY}
    files = {"file": (filename, audio, "audio/webm")}
    data = {"model": "saaras:v4", "mode": "transcribe"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, files=files, data=data)
        r.raise_for_status()
        return r.json()


def synthesize(text: str, lang: str) -> dict:
    """POST /text-to-speech, model bulbul:v3 -> {audios: [b64...]}."""
    url = f"{config.SARVAM_BASE}/text-to-speech"
    headers = {
        "api-subscription-key": config.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "bulbul:v3",
        "inputs": [text],
        "target_language_code": lang,
    }
    r = httpx.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    body = r.json()
    audios = body.get("audios", [])
    return {"audioBase64": audios[0] if audios else None, "cached": False}
