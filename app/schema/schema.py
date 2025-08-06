from pydantic import BaseModel, EmailStr

class CaseMetadata(BaseModel):
    caseId: str
    caseType: str

class EmailRequest(BaseModel):
    name: str
    company: str
    email: EmailStr
    message: str
