from typing import List, Optional

from pydantic import BaseModel


class FamilyMember(BaseModel):
    name: str
    relationship: str
    age: Optional[str] = None
    share: Optional[float] = None


class Affidavit(BaseModel):
    deceasedName: str
    applicantName: str
    relationship: str
    # ---- applicant details ----
    gender: Optional[str] = None  # "male" | "female"
    fatherName: Optional[str] = None
    applicantAge: Optional[str] = None
    applicantAddress: Optional[str] = None
    # ---- shareholding ----
    companyName: Optional[str] = None
    folioOrDpid: Optional[str] = None
    certificateNos: Optional[str] = None
    distinctiveNos: Optional[str] = None
    faceValue: Optional[str] = None
    numberOfShares: Optional[str] = None
    # ---- death ----
    dateOfDeath: Optional[str] = None
    placeOfDeath: Optional[str] = None
    familyTree: List[FamilyMember] = []
    noObjectionFrom: List[str] = []
