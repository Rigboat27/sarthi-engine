from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class EntityType(str, Enum):
    broker = "broker"
    listed_company = "listed company"
    rta = "RTA"
    iepf = "IEPF"


class GrievanceState(BaseModel):
    complaintCategory: Optional[str] = None
    entityName: Optional[str] = None
    entityType: Optional[EntityType] = None
    clientId: Optional[str] = None
    folioNo: Optional[str] = None
    dpid: Optional[str] = None
    issueSummaryEnglish: Optional[str] = None
    issueSummaryOriginal: Optional[str] = None
    incidentDate: Optional[str] = None
    amountInvolved: Optional[float] = None
    priorContactDate: Optional[str] = None
    priorContactProof: Optional[str] = None
    reliefSought: Optional[str] = None
    attachments: List[str] = []
    userLanguage: Optional[str] = None
