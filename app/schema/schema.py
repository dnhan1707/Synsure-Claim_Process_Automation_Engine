from fastapi import UploadFile, File, Form, Body
from pydantic import BaseModel, EmailStr
from typing import List


class EmailRequest(BaseModel):
    name: str
    company: str
    email: EmailStr
    message: str

class CaseSubmission(BaseModel):
    case_id: str = Form(None)
    case_name: str = Form(None)
    manual_input: str = Form(None)
    files: List[UploadFile] = File(None)

class BulkSubmitRequest(BaseModel):
    case_ids: List[str]

class BulkTaskStatusRequest(BaseModel):
    task_ids: List[str]

class TenantCreationRequest(BaseModel):
    tanant_name: str
