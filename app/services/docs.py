"""Doc scanner & legal builder (Team B's domain).

OCR, fuzzy name matching, and affidavit generation. Mock implementations here so
the portal can be wired and tested end-to-end before Team B's real pipeline lands;
Team B swaps the internals behind the same `/docs/*` contract.
"""

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

from app.models.affidavit import Affidavit


def _ratio(a: str, b: str) -> float:
    if fuzz:
        return fuzz.ratio(a.lower(), b.lower()) / 100.0
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


async def ocr(file) -> dict:
    """Mock OCR — returns a canned name so the name-mismatch check can be demoed."""
    _ = await file.read() if hasattr(file, "read") else None
    return {"text": "RAMESH SHARMA", "fields": {"name": "RAMESH SHARMA"}}


def match(a: str, b: str) -> dict:
    score = _ratio(a, b)
    return {
        "score": round(score, 4),
        "match": score >= 0.85,
        "a": a,
        "b": b,
    }


def affidavit(payload: dict) -> dict:
    aff = Affidavit(**payload)
    return {"affidavit": aff.model_dump(), "pdfBase64": None, "mock": True}
