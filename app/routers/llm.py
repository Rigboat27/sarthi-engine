from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app import config
from app.envelope import fail, ok
from app.services import gemini

router = APIRouter(prefix="/llm")


@router.post("/chat")
async def chat(payload: dict = Body(...)):
    messages = payload.get("messages", [])
    json_schema = payload.get("jsonSchema")

    if config.MOCK_MODE:
        return ok({"content": gemini.mock_reply(messages)}, tokens={"in": 0, "out": 0})

    try:
        text, usage = await gemini.chat(messages, json_schema)
        # Gemini free tier is zero-cost; this stays a hook for a paid swap.
        cost = 0.0
        config.add_spend(cost)
        return ok({"content": text}, tokens=usage, cost_inr=cost)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="llm_failed"))
