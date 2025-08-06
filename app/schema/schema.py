from pydantic import BaseModel

class CaseMetadata(BaseModel):
    caseId: str
    caseType: str

