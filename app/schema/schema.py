from fastapi import UploadFile, File, Form, Body
from pydantic import BaseModel, EmailStr
from typing import List,  Optional
from enum import Enum

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

class CaseStatus(str, Enum):
    open = "open"
    processing = "processing"
    closed = "closed"
    archived = "archived"


class MatchType(str, Enum):
    exact = "exact"
    size_only = "size_only"
    name_only = "name_only"

class FileInfo(BaseModel):
    filename: str
    size: Optional[int]

class ExistingFileInfo(BaseModel):
    id: str
    file: FileInfo
    uploaded_at: str

class DuplicateFileInfo(BaseModel):
    uploaded_file: FileInfo
    match_type: MatchType    
    existing_file: ExistingFileInfo

class DuplicateDataResponse(BaseModel):
    success: bool
    has_duplicate: bool
    duplicates: list[DuplicateFileInfo]
    new_files: list[FileInfo]


class FileActionType(str, Enum):
    replace = "replace"
    overwrite = "overwrite"
    keep_both = "keep_both"

class FileAction(BaseModel):
    # index: int
    action: FileActionType
    target_id: Optional[str]
