"""Doc scanner & legal builder (Team B's domain) — now Gemini-backed.

OCR (vision) and affidavit generation run through Gemini via the engine's key.
Mock fallbacks keep the portal demoable with zero keys. The rapidfuzz text match
is retained for cheap, deterministic comparison.
"""

import json
import re

from app import config
from app.models.affidavit import Affidavit
from app.services import gemini

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


def _parse_json(raw: str) -> dict:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            return json.loads(m.group(0))
        raise ValueError("could not parse model output as JSON")


# ---- text match (deterministic, no LLM) ----

def _ratio(a: str, b: str) -> float:
    if fuzz:
        return fuzz.ratio(a.lower(), b.lower()) / 100.0
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match(a: str, b: str) -> dict:
    score = _ratio(a, b)
    return {"score": round(score, 4), "match": score >= 0.85, "a": a, "b": b}


# ---- OCR: compare KYC vs certificate names (Gemini Vision) ----

OCR_PROMPT = (
    "You are a strict data extraction bot. I am providing two images.\n"
    "Image 1 is a KYC Document (Aadhaar, PAN, etc.). Image 2 is a Share Certificate or dividend warrant.\n"
    "Extract the FULL NAME of the individual from both documents.\n"
    "Check if the names are an EXACT MATCH (ignoring case, but sensitive to initials, middle names, and spelling).\n"
    "Return a raw JSON object with no markdown formatting:\n"
    '{"kycName": "Extracted Name 1", "certificateName": "Extracted Name 2", "isMatch": true/false}'
)


async def ocr(kyc_data_url: str, cert_data_url: str) -> dict:
    if config.MOCK_MODE or not config.GEMINI_API_KEY:
        return {
            "kycName": "RAMESH SHARMA",
            "certificateName": "RAMESH SHARM",
            "isMatch": False,
        }

    contents = [
        {
            "role": "user",
            "parts": [
                {"text": OCR_PROMPT},
                gemini.inline_image(kyc_data_url),
                gemini.inline_image(cert_data_url),
            ],
        }
    ]
    resp = await gemini.generate(
        "gemini-2.5-flash",
        {
            "contents": contents,
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        },
    )
    return _parse_json(gemini.extract_text(resp))


# ---- affidavit generation (Gemini) ----

MOCK_AFFIDAVIT_TEXT = (
    "AFFIDAVIT FOR TRANSMISSION OF SHARES\n\n"
    "I, {applicant}, legal heir of late {deceased}, do hereby solemnly affirm and declare:\n"
    "1. That {deceased} held the securities described in the transmission request.\n"
    "2. That {deceased} passed away, leaving the legal heirs listed in the attached family tree.\n"
    "3. That I am the rightful claimant and there is no dispute among the heirs.\n"
    "4. That this affidavit is executed to enable transmission of the said securities to my name.\n\n"
    "Deponent: {applicant}\nPlace: ____\nDate: ____"
)

MOCK_CHECKLIST = [
    "Obtain original + attested copies of the death certificate.",
    "Get No-Objection Certificates signed by every other legal heir.",
    "Fill the RTA's Transmission Request Form.",
    "Notarize this affidavit together with KYC documents.",
    "Submit the packet to the RTA / Depository Participant.",
    "Track the acknowledgment and follow up until the shares are transmitted.",
]


def _affidavit_prompt(a: Affidavit) -> str:
    survivors = "None"
    if a.familyTree:
        survivors = ", ".join(f"{m.name} ({m.relationship})" for m in a.familyTree)
    return (
        "You are a legal document generator copilot for SEBI and IEPF claims in India.\n"
        'Generate a formal "Affidavit for Transmission of Shares" (or general NOC) based on these facts:\n'
        f"Deceased Shareholder Name: {a.deceasedName}\n"
        f"Claimant (Legal Heir) Name: {a.applicantName}\n"
        f"Relation to Deceased: {a.relationship}\n"
        f"Other Surviving Family Members: {survivors}\n\n"
        "Write a professional, standard Indian legal affidavit in plain English.\n"
        "Also, generate a customized step-by-step to-do list (checklist) for the user explaining exactly what physical actions they must take next "
        "(e.g. obtaining NOCs from specific family members mentioned, notarizing, sending to the RTA).\n\n"
        "Return ONLY a raw JSON object with this exact structure (no markdown, no quotes outside JSON):\n"
        '{"affidavitText": "Full text of the affidavit...", "checklist": ["Step 1", "Step 2"]}'
    )


async def affidavit(payload: dict) -> dict:
    aff = Affidavit(**payload)
    if config.MOCK_MODE or not config.GEMINI_API_KEY:
        return {
            "affidavit": aff.model_dump(),
            "affidavitText": MOCK_AFFIDAVIT_TEXT.format(
                deceased=aff.deceasedName, applicant=aff.applicantName
            ),
            "checklist": MOCK_CHECKLIST,
            "pdfBase64": None,
            "mock": True,
        }

    resp = await gemini.generate(
        "gemini-2.5-flash",
        {
            "contents": [{"role": "user", "parts": [{"text": _affidavit_prompt(aff)}]}],
            "generationConfig": {"temperature": 0.2},
        },
    )
    parsed = _parse_json(gemini.extract_text(resp))
    return {
        "affidavit": aff.model_dump(),
        "affidavitText": parsed.get("affidavitText", ""),
        "checklist": parsed.get("checklist", []),
        "pdfBase64": None,
        "mock": False,
    }
