from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AccountType(str, Enum):
    bank = "bank"
    demat = "demat"
    mutual_fund = "mutual_fund"
    insurance = "insurance"
    ppf = "ppf"
    fd = "fd"


class Nominee(BaseModel):
    name: str
    relationship: str
    verified: bool


class Holding(BaseModel):
    id: str
    type: AccountType
    provider: str
    providerCode: str
    label: str
    maskedNumber: Optional[str] = None
    value: Optional[float] = None
    identifier: Optional[str] = None
    detail: Optional[str] = None
    fixUrl: Optional[str] = None
    nominee: Optional[Nominee] = None
