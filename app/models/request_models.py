from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import UploadFile

# Submission models
class SubmitFilesRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    case_id: str = Field(..., description="Case ID")
    chosen_files: List[str] = Field(..., description="List of file IDs to process")

class BatchSubmissionRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    case_ids: List[str] = Field(..., description="List of case IDs to process")

# File upload models
class DuplicateCheckRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    case_id: str = Field(..., description="Case ID")

class FileActionItem(BaseModel):
    target_id: str = Field(..., description="Target file ID (empty for new files)")
    action: str = Field(..., description="Action to take: upload, overwrite, keep")

class UploadFilesRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    case_id: str = Field(..., description="Case ID")
    file_actions: List[FileActionItem] = Field(..., description="Actions for each file")

# Task models
class ProcessTaskRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to process")

# Response models
class StandardResponse(BaseModel):
    success: bool
    error: Optional[str] = None

class CaseResponse(StandardResponse):
    new_case_id: Optional[str] = None
    result: Optional[dict] = None

class SubmissionResponse(StandardResponse):
    result: Optional[dict] = None

class BatchResponse(StandardResponse):
    message: Optional[str] = None
    task_ids: Optional[dict] = None
    status_check_info: Optional[str] = None


# Claim Manager models
class CreateClaimRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    case_name: str = Field(..., description="Name of the claim/case")

class UpdateClaimNameRequest(BaseModel):
    new_name: str = Field(..., description="New name for the claim")

class RemoveFilesRequest(BaseModel):
    file_ids: List[str] = Field(..., description="List of file IDs to remove", min_items=1)

# Tenant models  
class TenantCreationRequest(BaseModel):
    tenant_name: str = Field(..., description="Name of the tenant", min_length=1)

# Response models
class ClaimResponse(StandardResponse):
    result: Optional[dict] = None

class ClaimsListResponse(StandardResponse):
    result: Optional[List[dict]] = None

class TenantResponse(StandardResponse):
    result: Optional[dict] = None

class TenantsListResponse(StandardResponse):
    result: Optional[List[dict]] = None