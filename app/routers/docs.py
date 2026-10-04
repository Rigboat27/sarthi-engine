import base64

from fastapi import APIRouter, Body, File, UploadFile
from fastapi.responses import JSONResponse

from app.envelope import fail, ok
from app.services import docs as docs_service

router = APIRouter(prefix="/docs")


async def _to_data_url(file: UploadFile) -> str:
    data = await file.read()
    b64 = base64.b64encode(data).decode("ascii")
    mime = file.content_type or "image/jpeg"
    return f"data:{mime};base64,{b64}"


@router.post("/ocr")
async def ocr(kyc: UploadFile = File(...), cert: UploadFile = File(...)):
    try:
        kyc_url = await _to_data_url(kyc)
        cert_url = await _to_data_url(cert)
        return ok(await docs_service.ocr(kyc_url, cert_url))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="ocr_failed"))


@router.post("/match")
def match(payload: dict = Body(...)):
    return ok(docs_service.match(payload.get("a", ""), payload.get("b", "")))


@router.post("/affidavit")
def affidavit(payload: dict = Body(...)):
    try:
        return ok(docs_service.affidavit(payload))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="affidavit_failed"))


@router.post("/name-affidavit")
async def name_affidavit(payload: dict = Body(...)):
    try:
        return ok(await docs_service.name_affidavit(payload))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="name_affidavit_failed"))


@router.post("/vault-pdf")
def vault_pdf(payload: dict = Body(...)):
    try:
        return ok(docs_service.vault_pdf(payload))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=fail(str(e), code="vault_pdf_failed"))
