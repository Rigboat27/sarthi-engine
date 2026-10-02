from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app import config
from app.envelope import fail, ok
from app.services import sarvam

router = APIRouter(prefix="/speech")

# Mock transcripts cycle deterministically so a zero-spend demo reads naturally.
MOCK_TRANSCRIPTS = [
    ("vanakkam", "ta"),
    ("my broker has not credited my sale proceeds", "en"),
    ("mera paisa nahi aaya", "hi"),
]


@router.post("/stt")
async def stt(file: UploadFile = File(...), lang: str = Form("auto")):
    if config.MOCK_MODE:
        idx = sarvam.mock_tick()
        text, detected = MOCK_TRANSCRIPTS[idx % len(MOCK_TRANSCRIPTS)]
        return ok({"text": text, "detectedLanguage": detected})
    try:
        data = await sarvam.transcribe(await file.read(), file.filename or "audio.webm")
        return ok(data)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="stt_failed"))


@router.post("/tts")
def tts(payload: dict = Body(...)):
    text = payload.get("text", "")
    lang = payload.get("lang", "en")
    if config.MOCK_MODE:
        return ok({"audioBase64": None, "cached": True})
    try:
        return ok(sarvam.synthesize(text, lang))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="tts_failed"))
