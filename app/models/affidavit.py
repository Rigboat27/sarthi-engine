from typing import List, Optional

from pydantic import BaseModel


class FamilyMember(BaseModel):
    name: str
    relationship: str
    share: Optional[float] = None


class Affidavit(BaseModel):
    deceasedName: str
    applicantName: str
    relationship: str
    folioOrDpid: Optional[str] = None
    familyTree: List[FamilyMember]
    noObjectionFrom: List[str] = []
