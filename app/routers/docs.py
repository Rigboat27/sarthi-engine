from fastapi import APIRouter, Body, File, UploadFile

from app.envelope import ok
from app.services import docs as docs_service

router = APIRouter(prefix="/docs")


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    return ok(await docs_service.ocr(file))


@router.post("/match")
def match(payload: dict = Body(...)):
    return ok(docs_service.match(payload.get("a", ""), payload.get("b", "")))


@router.post("/affidavit")
def affidavit(payload: dict = Body(...)):
    return ok(docs_service.affidavit(payload))
