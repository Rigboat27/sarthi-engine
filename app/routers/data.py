import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.envelope import fail, ok

router = APIRouter(prefix="/data")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@router.get("/rules")
def rules():
    p = DATA_DIR / "scoresRules.json"
    if not p.exists():
        return JSONResponse(status_code=404, content=fail("rules not found"))
    return ok(json.loads(p.read_text(encoding="utf-8")))


@router.get("/brokers")
def brokers(name: str | None = None):
    p = DATA_DIR / "brokerDirectory.json"
    if not p.exists():
        return JSONResponse(status_code=404, content=fail("broker directory not found"))
    data = json.loads(p.read_text(encoding="utf-8"))
    brokers_list = data.get("brokers", [])
    if name:
        brokers_list = [b for b in brokers_list if name.lower() in b.get("name", "").lower()]
    return ok({"brokers": brokers_list})
