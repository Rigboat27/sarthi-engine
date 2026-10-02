import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.aa import mock_data
from app.envelope import fail, ok

router = APIRouter(prefix="/aa")

AGGREGATORS = [
    {"id": "onemoney", "name": "OneMoney", "tagline": "Consent-based financial data sharing"},
    {"id": "cams", "name": "CAMS Finserv", "tagline": "India's trusted AA & RTA network"},
    {"id": "finvu", "name": "Finvu", "tagline": "Open finance by Sahamati"},
    {"id": "setu", "name": "Setu AA", "tagline": "Data gateway for Bharat"},
]

# In-memory consent store: consentId -> {aggregatorId, scopes, verified}
_consents: dict[str, dict] = {}


@router.get("/aggregators")
def aggregators():
    return ok({"aggregators": AGGREGATORS})


@router.post("/consent")
def consent(payload: dict = Body(...)):
    aggregator_id = payload.get("aggregatorId")
    scopes = payload.get("scopes", [])
    if not aggregator_id:
        return JSONResponse(status_code=400, content=fail("aggregatorId is required"))

    cid = f"ca-{uuid.uuid4().hex[:12]}"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    _consents[cid] = {"aggregatorId": aggregator_id, "scopes": scopes, "verified": False}

    artefact = {
        "consentId": cid,
        "purpose": "Wealth mapping & nominee check",
        "purposeCode": "FI-ACCOUNT",
        "fipTypes": ["DEPOSIT", "INVESTMENTS", "INSURANCE", "PPF"],
        "expiresAt": expires,
    }
    return ok({"consentId": cid, "artefact": artefact})


@router.post("/verify")
def verify(payload: dict = Body(...)):
    cid = payload.get("consentId")
    rec = _consents.get(cid)
    if not rec:
        return JSONResponse(status_code=404, content=fail("consent not found", code="consent_not_found"))
    rec["verified"] = True
    return ok({"verified": True})


@router.post("/fetch")
def fetch(payload: dict = Body(...)):
    cid = payload.get("consentId")
    rec = _consents.get(cid)
    if not rec:
        return JSONResponse(status_code=404, content=fail("consent not found", code="consent_not_found"))
    if not rec["verified"]:
        return JSONResponse(
            status_code=403, content=fail("consent not verified", code="consent_not_verified")
        )

    holdings = mock_data.filter_by_scopes(rec["scopes"])
    fips = mock_data.to_fips(holdings)
    return ok({"consentId": cid, "fips": fips})
