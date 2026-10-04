"""Doc scanner & legal builder (Team B's domain).

- OCR (Gemini Vision) compares KYC vs certificate names.
- Affidavits are generated from the official SEBI format (deterministic template,
  no LLM hallucination) and rendered to a professional PDF.
- The rapidfuzz text match is retained for cheap, deterministic comparison.
"""

import base64
import io
import json
import os
import re
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import config
from app.models.affidavit import Affidavit
from app.services import gemini

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


# ---- Unicode (Devanagari) font for names in PDFs ----

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
_DEVA_FONT = "Devanagari"
_DEVA_BOLD = "Devanagari-Bold"


def _register_fonts() -> None:
    for name, fname in (
        (_DEVA_FONT, "NotoSansDevanagari-Regular.ttf"),
        (_DEVA_BOLD, "NotoSansDevanagari-Bold.ttf"),
    ):
        path = os.path.join(_FONT_DIR, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:  # noqa: BLE001
                pass


_register_fonts()


def _u(text: str) -> str:
    """Wrap text in a Devanagari-capable font if it contains non-ASCII, else escape."""
    if any(ord(c) > 127 for c in text):
        return f'<font name="{_DEVA_FONT}">{escape(text)}</font>'
    return escape(text)


def _parse_json(raw: str) -> dict:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            return json.loads(m.group(0))
        raise ValueError("could not parse model output as JSON")


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


def render_pdf(title: str, body: str) -> str:
    """Render plain text to a simple A4 PDF and return it as base64."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=16, spaceAfter=16, alignment=TA_CENTER)
    body_style = ParagraphStyle("B", parent=styles["BodyText"], fontSize=11, leading=17)
    story = [Paragraph(escape(title), title_style)]
    story.append(Paragraph("<br/>".join(escape(line) for line in body.split("\n")), body_style))
    doc.build(story)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Transmission affidavit — official SEBI format, deterministic
# ---------------------------------------------------------------------------

def _rel_word(gender: str | None, relationship: str) -> str:
    if gender == "male":
        return "son"
    if gender == "female":
        return "daughter"
    r = (relationship or "").lower()
    if any(w in r for w in ("wife", "spouse", "husband", "पत्नी", "पति")):
        return "spouse"
    if "daughter" in r or "बेटी" in r or "மகள்" in r:
        return "daughter"
    return "son"


def _parent_name(a: Affidavit) -> str:
    """Fill the 'son/daughter/spouse of ____' blank (father for child, deceased for spouse)."""
    if _rel_word(a.gender, a.relationship) == "spouse":
        return a.deceasedName or "________"
    return a.fatherName or "________"


def build_transmission_text(a: Affidavit) -> str:
    blank = "________"
    heirs = a.familyTree or []
    rel = _rel_word(a.gender, a.relationship)

    lines: list[str] = []
    lines.append(
        "FORMAT OF AFFIDAVIT FOR TRANSMISSION OF SHARES WITHOUT PRODUCING "
        "PROBATE / SUCCESSION CERTIFICATE / LETTERS OF ADMINISTRATION"
    )
    lines.append("")
    lines.append("AFFIDAVIT")
    lines.append("")
    lines.append(
        f"I, {a.applicantName or blank}, {rel} of {_parent_name(a)} aged {a.applicantAge or blank}, "
        f"an Indian Inhabitant / NRI presently residing at {a.applicantAddress or blank}, "
        "do hereby solemnly affirm and declare as under:"
    )
    lines.append("")
    lines.append(
        f"1. That Shri/Smt. {a.deceasedName or blank}, the deceased, was holding "
        f"{a.numberOfShares or blank} equity shares in {a.companyName or blank} covered under "
        f"Folio No. {a.folioOrDpid or blank} and Share Certificate No(s). {a.certificateNos or blank}, "
        f"bearing Distinctive Nos. {a.distinctiveNos or blank} of the face value of "
        f"Rs. {a.faceValue or blank}/- each."
    )
    lines.append("")
    lines.append("Folio No.     Certificate Nos.     Distinctive Nos.     Shares covered in each certificate")
    lines.append(f"{a.folioOrDpid or blank}     {a.certificateNos or blank}     {a.distinctiveNos or blank}     {a.numberOfShares or blank}")
    lines.append("")
    lines.append(
        f"2. Shri./Smt. {a.deceasedName or blank} expired intestate on "
        f"{a.dateOfDeath or blank} at {a.placeOfDeath or blank} leaving behind him/her "
        "the following legal heirs :"
    )
    lines.append("")
    lines.append("Sr. No.      Name of the heir      Age      Relation with the deceased")
    if heirs:
        for i, m in enumerate(heirs, 1):
            lines.append(f"{i}.           {m.name}      {m.age or blank}      {m.relationship}")
    else:
        lines.append("1.           ________      ____      ________")
    lines.append("")
    lines.append(
        "3. The abovementioned shares were separate and self acquired property of the "
        "deceased. According to the law of Intestate Succession applicable to him/her by "
        "which he/she was governed at the time of his/her death, the person(s) mentioned "
        f"hereinabove is/are the only heir(s) of the deceased. They are entitled to inherit "
        f"the aforesaid shares covered under Folio No. {a.folioOrDpid or blank} held by the deceased."
    )
    lines.append("")
    lines.append(
        f"4. That the Late Shri/Smt. {a.deceasedName or blank} has left no other heir than "
        "these in paragraph 2 above and the person(s) mentioned therein is/are only his/her "
        "legal heir(s)."
    )
    lines.append("")
    lines.append(
        "5. I have already executed indemnity bond for transmitting the aforesaid shares held "
        "by the deceased in my name without production of Succession Certificate / Probate of "
        "Will / Letter of Administration (LoA)."
    )
    lines.append("")
    lines.append(
        f"6. I therefore request the {a.companyName or blank} to transmit the above shares in "
        "my / our name."
    )
    lines.append("")
    lines.append("I am executing this declaration to be submitted to the concerned authorities of the Company.")
    lines.append("")
    lines.append("VERIFICATION")
    lines.append("I hereby state that whatever is stated herein above are true to the best of my knowledge.")
    lines.append("")
    lines.append(f"Solemnly affirmed at {blank}")
    lines.append(f"On this {blank} day of {blank} 20..")
    lines.append("")
    lines.append("(Signature of the Applicant/s)")
    lines.append("Deponent")
    lines.append("")
    lines.append("Identified by me                      Before Me")
    lines.append("")
    lines.append("Advocate                              S.E.O. / Oaths Commissioner / Notary")
    lines.append("")
    lines.append("NOTES:")
    lines.append("1. Affidavit should be on Non-judicial stamp paper of Rs. 100/-, or duly Franked and duly attested and affirmed by Notary.")
    lines.append("2. It should be executed by the Applicant(s).")
    lines.append("3. Maximum of only three legal heirs can apply for transmission.")
    return "\n".join(lines)


def build_checklist(a: Affidavit) -> list[str]:
    steps = [
        "Print this affidavit on ₹100 non-judicial stamp paper (or duly franked).",
        "Get the affidavit notarized / affirmed before a Notary or Oaths Commissioner.",
    ]
    for m in a.familyTree or []:
        steps.append(f"Obtain a signed No-Objection Certificate from {m.name} ({m.relationship}).")
    steps += [
        "Fill the RTA's Transmission Request Form and attach an indemnity bond.",
        "Submit the full packet (affidavit + NOCs + indemnity bond + KYC) to the RTA / DP.",
        "Track the acknowledgment until the shares are transmitted to your name.",
    ]
    return steps


def render_transmission_pdf(a: Affidavit) -> str:
    """Render the transmission affidavit to an official-looking PDF.

    Times New Roman (reportlab's Times family), underlined/centred title,
    populated folio + heirs tables, verification on its own page, centred notes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()

    ROMAN = "Times-Roman"
    BOLD = "Times-Bold"

    title = ParagraphStyle("t", parent=styles["Normal"], fontName=BOLD, fontSize=9, leading=12, alignment=TA_CENTER)
    heading = ParagraphStyle("h", parent=styles["Normal"], fontName=BOLD, fontSize=14, leading=18, alignment=TA_CENTER, spaceBefore=6, spaceAfter=14)
    body = ParagraphStyle("b", parent=styles["Normal"], fontName=ROMAN, fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=8)
    sig = ParagraphStyle("s", parent=styles["Normal"], fontName=ROMAN, fontSize=10.5, leading=15, alignment=TA_RIGHT)
    idb = ParagraphStyle("i", parent=styles["Normal"], fontName=ROMAN, fontSize=10.5, leading=15)
    note = ParagraphStyle("n", parent=styles["Normal"], fontName=ROMAN, fontSize=8.5, leading=12, alignment=TA_CENTER)
    note_head = ParagraphStyle("nh", parent=styles["Normal"], fontName=BOLD, fontSize=9, leading=12, alignment=TA_CENTER, spaceBefore=6)

    story: list = []

    # 1. centred, underlined, bold title
    story.append(Paragraph(f"<u>{escape(build_title_text())}</u>", title))
    story.append(Spacer(1, 6))
    # 2. "AFFIDAVIT" centred before the contents
    story.append(Paragraph("AFFIDAVIT", heading))

    story.append(Paragraph(
        f"I, {_u(a.applicantName or '________')}, {_rel_word(a.gender, a.relationship)} of {_u(_parent_name(a))} aged {a.applicantAge or '________'}, "
        f"an Indian Inhabitant / NRI presently residing at {_u(a.applicantAddress or '________')}, "
        "do hereby solemnly affirm and declare as under:",
        body,
    ))
    story.append(Paragraph(
        f"1. That Shri/Smt. {_u(a.deceasedName or '________')}, the deceased, was holding "
        f"{a.numberOfShares or '________'} equity shares in {_u(a.companyName or '________')} covered under "
        f"Folio No. {a.folioOrDpid or '________'} and Share Certificate No(s). {a.certificateNos or '________'}, "
        f"bearing Distinctive Nos. {a.distinctiveNos or '________'} of the face value of Rs. {a.faceValue or '________'}/- each.",
        body,
    ))

    # folio table (populated)
    folio_rows = [
        ["Folio No.", "Certificate Nos.", "Distinctive Nos.", "Shares covered in each certificate"],
        [a.folioOrDpid or "________", a.certificateNos or "________", a.distinctiveNos or "________", a.numberOfShares or "________"],
    ]
    ft = Table(folio_rows, colWidths=[1.2 * inch, 1.8 * inch, 1.9 * inch, 1.7 * inch])
    ft.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BOLD),
        ("FONTNAME", (0, 1), (-1, -1), ROMAN),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ft)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"2. Shri./Smt. {_u(a.deceasedName or '________')} expired intestate on "
        f"{a.dateOfDeath or '________'} at {_u(a.placeOfDeath or '________')} leaving behind him/her the following legal heirs :",
        body,
    ))

    # heirs table (proper column spacing)
    heirs = a.familyTree or []
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontName=ROMAN, fontSize=9.5, leading=12)
    rows = [["Sr. No.", "Name of the heir", "Age", "Relation with the deceased"]]
    if heirs:
        for i, m in enumerate(heirs, 1):
            rows.append([
                str(i),
                Paragraph(_u(m.name), cell_style),
                m.age or "—",
                Paragraph(_u(m.relationship), cell_style),
            ])
    else:
        rows.append(["1", "________", "____", "________"])
    ht = Table(rows, colWidths=[0.7 * inch, 2.4 * inch, 0.8 * inch, 2.5 * inch])
    ht.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BOLD),
        ("FONTNAME", (0, 1), (-1, -1), ROMAN),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ht)
    story.append(Spacer(1, 10))

    story.append(Paragraph(escape("3. The abovementioned shares were separate and self acquired property of the deceased. According to the law of Intestate Succession applicable to him/her, the person(s) mentioned hereinabove is/are the only heir(s) of the deceased and are entitled to inherit the aforesaid shares held by the deceased."), body))
    story.append(Paragraph(f"4. That the Late Shri/Smt. {_u(a.deceasedName or '________')} has left no other heir than these in paragraph 2 above and the person(s) mentioned therein is/are only his/her legal heir(s).", body))
    story.append(Paragraph(escape("5. I have already executed indemnity bond for transmitting the aforesaid shares held by the deceased in my name without production of Succession Certificate / Probate of Will / Letter of Administration (LoA)."), body))
    story.append(Paragraph(f"6. I therefore request the {_u(a.companyName or '________')} to transmit the above shares in my / our name.", body))
    story.append(Paragraph(escape("I am executing this declaration to be submitted to the concerned authorities of the Company."), body))

    # verification on its own page
    story.append(PageBreak())
    story.append(Paragraph("VERIFICATION", ParagraphStyle("v", parent=styles["Normal"], fontName=BOLD, fontSize=11, spaceAfter=10)))
    story.append(Paragraph("I hereby state that whatever is stated herein above are true to the best of my knowledge.", body))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Solemnly affirmed at ________", sig))
    story.append(Paragraph("On this ____ day of ________ 20..", sig))
    story.append(Spacer(1, 8))
    story.append(Paragraph("(Signature of the Applicant/s)", sig))
    story.append(Paragraph("Deponent", sig))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Identified by me&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Before Me", idb))
    story.append(Paragraph("Advocate&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;S.E.O. / Oaths Commissioner / Notary", idb))

    # centred notes
    story.append(Spacer(1, 18))
    story.append(Paragraph("NOTES:", note_head))
    for n in [
        "1. Affidavit should be on Non-judicial stamp paper of Rs. 100/-, or duly Franked and duly attested and affirmed by Notary.",
        "2. It should be executed by the Applicant(s).",
        "3. Maximum of only three legal heirs can apply for transmission.",
    ]:
        story.append(Paragraph(escape(n), note))

    doc.build(story)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_title_text() -> str:
    return (
        "FORMAT OF AFFIDAVIT FOR TRANSMISSION OF SHARES WITHOUT PRODUCING "
        "PROBATE / SUCCESSION CERTIFICATE / LETTERS OF ADMINISTRATION"
    )


def _format_inr(value) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def render_vault_pdf(owner: str, accounts: list[dict]) -> str:
    """Render the Legacy Wealth Vault as an official-looking PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    ROMAN = "Times-Roman"
    BOLD = "Times-Bold"

    title = ParagraphStyle("t", parent=styles["Normal"], fontName=BOLD, fontSize=15, leading=19, alignment=TA_CENTER)
    sub = ParagraphStyle("s", parent=styles["Normal"], fontName=ROMAN, fontSize=9.5, leading=13, alignment=TA_CENTER, spaceAfter=16)
    cell = ParagraphStyle("c", parent=styles["Normal"], fontName=ROMAN, fontSize=9, leading=12)
    note = ParagraphStyle("n", parent=styles["Normal"], fontName=ROMAN, fontSize=8.5, leading=12, alignment=TA_CENTER, spaceBefore=14)

    story: list = []
    story.append(Paragraph("SARTHI VIRAASAT", title))
    story.append(Paragraph("LEGACY WEALTH VAULT", title))
    story.append(Paragraph(
        f"Account Holder: {_u(owner)} &nbsp;·&nbsp; Generated on {datetime.now().strftime('%d %B %Y')} &nbsp;·&nbsp; "
        f"{len(accounts)} accounts mapped",
        sub,
    ))

    rows = [["Sr.", "Provider", "Account", "Nominee", "Approx. Value"]]
    for i, acc in enumerate(accounts, 1):
        label = acc.get("label", "")
        masked = acc.get("maskedNumber")
        rows.append([
            str(i),
            Paragraph(_u(acc.get("provider", "")), cell),
            f"{label}{' ' + masked if masked else ''}",
            Paragraph(_u(acc.get("nomineeName") or "NO NOMINEE"), cell),
            _format_inr(acc.get("value")),
        ])

    tbl = Table(rows, colWidths=[0.4 * inch, 1.5 * inch, 2.0 * inch, 1.6 * inch, 1.1 * inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BOLD),
        ("FONTNAME", (0, 1), (-1, -1), ROMAN),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)

    story.append(Paragraph(
        "This Legacy Wealth Vault is a self-declared record of the account holder's "
        "financial footprint. Share it only with a trusted family member. "
        "Accounts marked 'NO NOMINEE' need a nominee registered immediately.",
        note,
    ))

    doc.build(story)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def vault_pdf(payload: dict) -> dict:
    owner = payload.get("owner", "Account Holder")
    accounts = payload.get("accounts", [])
    return {"pdfBase64": render_vault_pdf(owner, accounts)}


def affidavit(payload: dict) -> dict:
    """Build the transmission affidavit (deterministic) and render its PDF."""
    a = Affidavit(**payload)
    text = build_transmission_text(a)
    checklist = build_checklist(a)
    return {
        "affidavit": a.model_dump(),
        "affidavitText": text,
        "checklist": checklist,
        "pdfBase64": render_transmission_pdf(a),
        "mock": False,
    }


# ---------------------------------------------------------------------------
# Name-discrepancy affidavit (IEPF OCR mismatch)
# ---------------------------------------------------------------------------

NAME_AFFIDAVIT_PROMPT = (
    "You are a legal document generator for SEBI and IEPF claims in India.\n"
    'Generate a formal "Affidavit for Name Discrepancy".\n'
    'The name on the KYC document (Aadhaar/PAN) is: "{kycName}".\n'
    'The name on the share certificate / dividend warrant is: "{certificateName}".\n'
    "The claimant asserts that both names refer to the SAME person and the difference is only a spelling/initials variation, not a change of identity.\n"
    "Write it in plain, formal English, ready to print and notarize.\n"
    "Return ONLY a raw JSON object: {\"affidavitText\": \"...\"}"
)

MOCK_NAME_AFFIDAVIT_TEXT = (
    "AFFIDAVIT FOR NAME DISCREPANCY\n\n"
    "I, {kyc}, son/daughter of ____, resident of ____, do hereby solemnly affirm and declare:\n"
    "1. That my name appears as \"{kyc}\" in my KYC records (Aadhaar / PAN).\n"
    "2. That the same name appears as \"{cert}\" on the relevant share certificate / dividend warrant.\n"
    "3. That both names refer to one and the same person, namely myself, and the difference is due to a spelling / initials variation.\n"
    "4. That I make this declaration to enable processing of my IEPF claim.\n\n"
    "Deponent: {kyc}\nPlace: ____\nDate: ____"
)


async def name_affidavit(payload: dict) -> dict:
    kyc = payload.get("kycName", "")
    cert = payload.get("certificateName", "")
    title = "Affidavit for Name Discrepancy"

    if config.MOCK_MODE or not config.GEMINI_API_KEY:
        text = MOCK_NAME_AFFIDAVIT_TEXT.format(kyc=kyc, cert=cert)
        return {"affidavitText": text, "pdfBase64": render_pdf(title, text), "mock": True}

    prompt = NAME_AFFIDAVIT_PROMPT.format(kycName=kyc, certificateName=cert)
    resp = await gemini.generate_with_fallback(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        },
    )
    parsed = _parse_json(gemini.extract_text(resp))
    text = parsed.get("affidavitText", "")
    return {"affidavitText": text, "pdfBase64": render_pdf(title, text), "mock": False}


# ---------------------------------------------------------------------------
# OCR: compare KYC vs certificate names (Gemini Vision)
# ---------------------------------------------------------------------------

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
    resp = await gemini.generate_with_fallback(
        {
            "contents": contents,
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        },
    )
    return _parse_json(gemini.extract_text(resp))
