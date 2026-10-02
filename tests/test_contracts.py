"""Contract tests: validate the engine's outputs against the sarthi-contracts schemas.

Runs when the sarthi-contracts repo is checked out beside sarthi-engine
(../sarthi-contracts). Skips cleanly otherwise — the point is to catch drift
between what the engine serves and the shared JSON Schemas.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
validate = jsonschema.validate

from app.aa import mock_data  # noqa: E402
from app.envelope import fail, ok  # noqa: E402
from app.models.affidavit import Affidavit, FamilyMember  # noqa: E402
from app.models.grievance import GrievanceState  # noqa: E402

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "sarthi-contracts" / "schemas"


def load(name: str) -> dict:
    p = SCHEMAS_DIR / name
    if not p.exists():
        pytest.skip(f"schema {name} not found at {SCHEMAS_DIR}")
    return json.loads(p.read_text(encoding="utf-8"))


def test_holdings_conform():
    schema = load("holding.schema.json")
    for h in mock_data.HOLDINGS:
        validate(h.model_dump(), schema)


def test_aa_fetch_response_conforms():
    schema = load("aaFetchResponse.schema.json")
    fips = mock_data.to_fips(mock_data.HOLDINGS)
    validate({"consentId": "ca-test", "fips": fips}, schema)


def test_grievance_state_conforms():
    schema = load("grievanceState.schema.json")
    gs = GrievanceState(
        complaintCategory="non-receipt of funds",
        entityName="Groww",
        entityType="broker",
        clientIdFolioNoDpid="ABCDE1234F",
        issueSummaryEnglish="Broker did not credit sale proceeds.",
        issueSummaryOriginal="मेरा पैसा नहीं आया",
        incidentDate="2026-03-03",
        amountInvolved=40000,
        priorContactProof="emailed",
        priorContactConfirmed=True,
        reliefSought="Credit my sale proceeds",
        userLanguage="hi-IN",
    )
    validate(gs.model_dump(), schema)


def test_affidavit_conforms():
    schema = load("affidavit.schema.json")
    aff = Affidavit(
        deceasedName="Ramesh Sharma",
        applicantName="Priya Sharma",
        relationship="Spouse",
        familyTree=[FamilyMember(name="Arjun Sharma", relationship="Son", share=50)],
    )
    validate(aff.model_dump(), schema)


def test_envelope_conforms():
    schema = load("apiEnvelope.schema.json")
    validate(ok({"x": 1}), schema)
    validate(fail("boom"), schema)
