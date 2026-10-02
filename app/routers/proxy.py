"""Extension-compatible passthrough routes.

The Chrome extension "Saathi" (Team A) posts to these exact paths and expects
these exact response shapes. This router absorbs the job of the extension's old
Node proxy so there is ONE backend at :8787 for both the extension and the portal.

Shapes are deliberately NOT wrapped in the ApiEnvelope — the extension's
providers read the raw vendor shapes (text/detectedLang, audios[], candidates[]).
"""

import httpx
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, Response

from app import config

router = APIRouter()


# ---- STT (Sarvam Saaras v4). Extension reads { text, detectedLang }. ----
@router.post("/stt")
async def stt(request: Request):
    if config.MOCK_MODE:
        return {"text": "vanakkam, my broker has not credited my sale proceeds", "detectedLang": "ta-IN"}

    if not config.SARVAM_API_KEY:
        return JSONResponse(status_code=503, content={"error": "SARVAM_API_KEY not set"})

    content_type = request.headers.get("content-type", "multipart/form-data")
    body = await request.body()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{config.SARVAM_BASE}/speech-to-text",
            headers={"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": content_type},
            content=body,
        )
    if r.status_code != 200:
        return JSONResponse(status_code=r.status_code, content={"error": "stt failed", "detail": r.text[:300]})

    parsed = r.json()
    text = parsed.get("transcript") or parsed.get("text") or ""
    config.add_spend((5.0 / 3600) * config.STT_RATE_PER_HOUR)  # flat 5s/clip estimate
    return {"text": text, "detectedLang": "unknown", "spentINR": round(config.spent(), 3)}


# ---- TTS (Sarvam Bulbul v3). Passthrough: extension reads { audios: [b64] }. ----
@router.post("/tts")
async def tts(payload: dict = Body(...)):
    if config.MOCK_MODE:
        return {"audios": [""]}

    if not config.SARVAM_API_KEY:
        return JSONResponse(status_code=503, content={"error": "SARVAM_API_KEY not set"})

    text = payload.get("text", "")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{config.SARVAM_BASE}/text-to-speech",
            headers={"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "language_code": payload.get("language_code", "en-IN"),
                "model": payload.get("model", "bulbul:v3"),
                "speaker": payload.get("speaker", "anushka"),
            },
        )
    config.add_spend((len(text) / 10_000) * config.TTS_RATE_PER_10K_CHARS)
    return Response(content=r.content, media_type="application/json", status_code=r.status_code)


# ---- Gemini (conversation). Passthrough: extension reads raw candidates[]. ----
@router.post("/gemini/{path:path}")
async def gemini(path: str, request: Request):
    if config.MOCK_MODE:
        return {
            "candidates": [{"content": {"parts": [{"text": '{"reply":"Namaste.","detectedLanguage":"hi-IN"}'}]}}],
            "usageMetadata": {"promptTokenCount": 0, "candidatesTokenCount": 0},
        }

    if not config.GEMINI_API_KEY:
        return JSONResponse(status_code=503, content={"error": "GEMINI_API_KEY not set"})

    body = await request.body()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{config.GEMINI_BASE}/models/{path}",
            headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
            content=body,
        )
    return Response(content=r.content, media_type="application/json", status_code=r.status_code)


# ---- Sarvam chat completions (sarvam-30b). Passthrough. ----
@router.post("/sarvam/v1/chat/completions")
async def sarvam_llm(request: Request):
    if config.MOCK_MODE:
        return {"choices": [{"message": {"content": "{}"}}]}

    if not config.SARVAM_API_KEY:
        return JSONResponse(status_code=503, content={"error": "SARVAM_API_KEY not set"})

    body = await request.body()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{config.SARVAM_BASE}/v1/chat/completions",
            headers={"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": "application/json"},
            content=body,
        )
    return Response(content=r.content, media_type="application/json", status_code=r.status_code)
