from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class EntityType(str, Enum):
    broker = "broker"
    listed_company = "listed company"
    rta = "RTA"
    iepf = "IEPF"


class PriorContactProof(str, Enum):
    emailed = "emailed"
    none = "none"
    rejected = "rejected"


class Attachment(BaseModel):
    dataUrl: str
    name: str
    size: int
    type: str


class GrievanceState(BaseModel):
    complaintCategory: Optional[str] = None
    entityName: Optional[str] = None
    entityType: Optional[EntityType] = None
    clientIdFolioNoDpid: Optional[str] = None
    issueSummaryEnglish: Optional[str] = None
    issueSummaryOriginal: Optional[str] = None
    incidentDate: Optional[str] = None
    amountInvolved: Optional[float] = None
    priorContactDate: Optional[str] = None
    priorContactProof: Optional[PriorContactProof] = None
    priorContactConfirmed: bool = False
    priorContactTicket: Optional[str] = None
    userName: Optional[str] = None
    userPhone: Optional[str] = None
    soldDescription: Optional[str] = None
    reliefSought: Optional[str] = None
    attachments: List[Attachment] = []
    userLanguage: str = "en-IN"
    skippedFields: List[str] = []
