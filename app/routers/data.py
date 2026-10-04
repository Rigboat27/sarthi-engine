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
        needle = name.lower().strip()
        brokers_list = [
            b
            for b in brokers_list
            if any(needle in n.lower() or n.lower() in needle for n in b.get("names", []))
        ]
    return ok({"brokers": brokers_list})


@router.get("/nodal")
def nodal(company: str | None = None):
    """Route an IEPF claimant to the correct company + RTA (never a guessed address)."""
    p = DATA_DIR / "nodalOfficers.json"
    if not p.exists():
        return JSONResponse(status_code=404, content=fail("nodal officer directory not found"))
    data = json.loads(p.read_text(encoding="utf-8"))
    companies = data.get("companies", [])

    # Public Registrar & Transfer Agent investor-service emails.
    rta_email = {
        "KFin Technologies": "einward.ris@kfintech.com",
        "Link Intime India": "rnt.helpdesk@linkintime.co.in",
        "TSR Consultants": "tsrd@tsrdarashaw.com",
        "Alankit Assignments": "investorservices@alankit.com",
    }

    if company:
        needle = company.lower().strip()
        companies = [
            c
            for c in companies
            if needle in c.get("name", "").lower() or needle in c.get("ticker", "").lower()
        ]

    enriched = [
        {**c, "supportEmail": rta_email.get(c.get("rta", ""))}
        for c in companies
    ]

    return ok(
        {
            "companies": enriched,
            "warning": "The Nodal Officer's own mailing address is not yet verified — "
            "confirm it on the company's investor page before sending physical documents.",
        }
    )
