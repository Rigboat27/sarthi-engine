"""Mock Financial Information Provider (FIP) data for the AA sandbox.

Mirrors the real Account Aggregator shape: consent -> AA -> FIP -> Sarthi.
Swapping to a live Setu/Finvu sandbox is a data-source change only (the /aa/*
routes stay identical).
"""

from app.models.holding import AccountType, Holding, Nominee

HOLDINGS: list[Holding] = [
    Holding(
        id="bank-hdfc-savings",
        type=AccountType.bank,
        provider="HDFC Bank",
        providerCode="hdfc",
        label="Savings Account",
        maskedNumber="•••• 4521",
        identifier="50100XXXXX4521",
        value=185400,
        nominee=Nominee(name="Priya Sharma", relationship="Spouse", verified=True),
        detail="Salary account · Bengaluru",
        fixUrl="https://www.hdfcbank.com/personal/ways-to-bank/nominee",
    ),
    Holding(
        id="bank-sbi-savings",
        type=AccountType.bank,
        provider="State Bank of India",
        providerCode="sbi",
        label="Savings Account",
        maskedNumber="•••• 8890",
        identifier="30012XXXXX8890",
        value=42300,
        detail="Home-town branch · Lucknow",
        fixUrl="https://retail.onlinesbi.sbi/nominee.html",
    ),
    Holding(
        id="bank-icici-fd",
        type=AccountType.fd,
        provider="ICICI Bank",
        providerCode="icici",
        label="Fixed Deposit",
        maskedNumber="FD •••• 7712",
        identifier="FD-009812",
        value=250000,
        nominee=Nominee(name="Priya Sharma", relationship="Spouse", verified=True),
        detail="Matures Apr 2027",
        fixUrl="https://www.icicibank.com/nominee",
    ),
    Holding(
        id="demat-cdsl",
        type=AccountType.demat,
        provider="CDSL",
        providerCode="cdsl",
        label="Demat Account (BO ID)",
        maskedNumber="•••• 3318",
        identifier="1208XXXXXXXX3318",
        value=612750,
        detail="Via Zerodha · 14 holdings",
        fixUrl="https://www.cdslindia.com/cas/Nominee.html",
    ),
    Holding(
        id="demat-nsdl",
        type=AccountType.demat,
        provider="NSDL",
        providerCode="nsdl",
        label="Demat Account (DP ID)",
        maskedNumber="•••• 5594",
        identifier="IN300XXX",
        value=98000,
        nominee=Nominee(name="Arjun Sharma", relationship="Son", verified=True),
        detail="Via HDFC Securities",
        fixUrl="https://nsdl.co.in/nominee.php",
    ),
    Holding(
        id="mf-cams-1",
        type=AccountType.mutual_fund,
        provider="CAMS",
        providerCode="cams",
        label="Equity Fund Folio",
        maskedNumber="•••• 2244",
        identifier="98765432/44",
        value=305200,
        nominee=Nominee(name="Priya Sharma", relationship="Spouse", verified=True),
        detail="SIP active · ₹5,000/mo",
        fixUrl="https://www.mfcentral.com",
    ),
    Holding(
        id="mf-kfintech-1",
        type=AccountType.mutual_fund,
        provider="KFintech",
        providerCode="kfintech",
        label="ELSS Folio",
        maskedNumber="•••• 9081",
        identifier="55667788/90",
        value=120000,
        detail="Lock-in ended 2025",
        fixUrl="https://www.mfcentral.com",
    ),
    Holding(
        id="insurance-lic",
        type=AccountType.insurance,
        provider="LIC of India",
        providerCode="lic",
        label="Life Insurance Policy",
        maskedNumber="•••• 7715",
        identifier="Policy 29XXXXXXXX",
        value=1000000,
        nominee=Nominee(name="Priya Sharma", relationship="Spouse", verified=True),
        detail="Sum assured ₹10L",
        fixUrl="https://licindia.in/nominee",
    ),
    Holding(
        id="ppf-sbi",
        type=AccountType.ppf,
        provider="State Bank of India",
        providerCode="sbi",
        label="PPF Account",
        maskedNumber="•••• 6102",
        identifier="PPF-XXXX6102",
        value=347800,
        detail="Matures 2032",
        fixUrl="https://retail.onlinesbi.sbi/nominee.html",
    ),
]

# consent scope -> allowed account types
SCOPE_MAP: dict[str, list[AccountType]] = {
    "bank": [AccountType.bank, AccountType.fd, AccountType.ppf],
    "demat": [AccountType.demat],
    "mutual_fund": [AccountType.mutual_fund],
    "insurance": [AccountType.insurance],
}

FIP_TYPE: dict[AccountType, str] = {
    AccountType.bank: "DEPOSIT",
    AccountType.fd: "DEPOSIT",
    AccountType.ppf: "PPF",
    AccountType.demat: "INVESTMENTS",
    AccountType.mutual_fund: "INVESTMENTS",
    AccountType.insurance: "INSURANCE",
}


def filter_by_scopes(scopes: list[str]) -> list[Holding]:
    allowed: set[AccountType] = set()
    for s in scopes:
        allowed.update(SCOPE_MAP.get(s, []))
    if not allowed:
        return HOLDINGS
    return [h for h in HOLDINGS if h.type in allowed]


def to_fips(holdings: list[Holding]) -> list[dict]:
    """Group flat holdings into FIP records shaped like a Setu/Finvu response."""
    grouped: dict[tuple[str, str], list[Holding]] = {}
    for h in holdings:
        key = (FIP_TYPE[h.type], h.providerCode.upper())
        grouped.setdefault(key, []).append(h)

    fips = []
    for (ftype, fid), items in grouped.items():
        fips.append({"fipId": fid, "type": ftype, "data": [i.model_dump() for i in items]})
    return fips
