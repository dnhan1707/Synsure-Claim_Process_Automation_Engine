from fastapi import APIRouter, UploadFile, File, Form, Path, HTTPException, Security
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.controller.claim_manager_controller import ClaimManagerController
from app.models.request_models import (
    CreateClaimRequest, UpdateClaimNameRequest, RemoveFilesRequest,
    ClaimResponse, ClaimsListResponse, StandardResponse
)
from app.routes.auth_routes import get_current_user

import logging

logger = logging.getLogger(__name__)
claim_manager_controller = ClaimManagerController()

def create_claim_manager_routes() -> APIRouter:
    router = APIRouter(
        prefix="/claim/manager",
        tags=["Claims"],
        # dependencies=[Security(get_current_user)]
    )
    
    # Claims CRUD operations
    @router.post("/", response_model=StandardResponse)
    async def create_new_claim(
        tenant_id: str = Form(..., description="Tenant ID"),
        case_name: str = Form(..., description="Name of the claim/case"),
        files: Optional[List[UploadFile]] = File(None, description="Optional files to upload")
    ):
        """Create a new claim with optional file uploads."""
        try:
            res = await claim_manager_controller.create_new_claim(
                tenant_id=tenant_id,
                case_name=case_name,
                files=files
            )
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to create new claim"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": "Claim created successfully"}, 
                status_code=201
            )
        
        except Exception as e:
            logger.error(f"Error in create_new_claim: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    @router.get("/", response_model=ClaimsListResponse)
    async def get_all_claims():
        """Get all claims in the system."""
        try:
            res = await claim_manager_controller.get_all_claim()
            
            if not res:
                return JSONResponse(
                    {"success": False, "result": [], "error": "No claims found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in get_all_claims: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "result": [], "error": "Internal server error"}, 
                status_code=500
            )

    @router.get("/{claim_id}", response_model=ClaimResponse)
    async def get_claim_by_id(
        claim_id: str = Path(..., description="Claim ID to retrieve")
    ):
        """Get detailed information about a specific claim."""
        try:
            res = await claim_manager_controller.get_claim_by_id(claim_id)
            
            if not res:
                return JSONResponse(
                    {"success": False, "result": {}, "error": "Claim not found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in get_claim_by_id: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "result": {}, "error": "Internal server error"}, 
                status_code=500
            )

    @router.patch("/{claim_id}", response_model=StandardResponse)
    async def update_claim_name(
        claim_id: str = Path(..., description="Claim ID to update"),
        request: UpdateClaimNameRequest = None
    ):
        """Update the name of an existing claim."""
        try:
            res = await claim_manager_controller.update_claim_name(claim_id, request.new_name)
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to update claim name"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": "Claim name updated successfully"}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in update_claim_name: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    @router.delete("/{case_id}", response_model=StandardResponse)
    async def remove_case(
        case_id: str = Path(..., description="Case ID to remove")
    ):
        """Remove a case and all its associated files."""
        try:
            res = await claim_manager_controller.remove_case(case_id)
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to remove case"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": "Case successfully deleted"}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in remove_case: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    # File operations on existing cases
    @router.post("/{tenant_id}/{case_id}", response_model=StandardResponse)
    async def upload_files_to_existing_case(
        tenant_id: str = Path(..., description="Tenant ID"),
        case_id: str = Path(..., description="Case ID"),
        files: List[UploadFile] = File(..., description="Files to upload")
    ):
        """Upload files to an existing case."""
        try:
            if not files:
                return JSONResponse(
                    {"success": False, "error": "No files provided"}, 
                    status_code=400
                )

            res = await claim_manager_controller.upload_files_existed_case(
                tenant_id, case_id, files
            )
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to upload files"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": f"Successfully uploaded {len(files)} files"}, 
                status_code=201
            )

        except Exception as e:
            logger.error(f"Error in upload_files_to_existing_case: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    @router.put("/{tenant_id}/{case_id}/{file_id}", response_model=StandardResponse)
    async def replace_existing_file(
        tenant_id: str = Path(..., description="Tenant ID"),
        case_id: str = Path(..., description="Case ID"),
        file_id: str = Path(..., description="File ID to replace"),
        new_file: UploadFile = File(..., description="New file to replace the existing one")
    ):
        """Replace an existing file with a new one."""
        try:
            res = await claim_manager_controller.replace_existed_file(
                tenant_id, case_id, file_id, new_file
            )
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to replace file"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": "File replaced successfully"}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in replace_existing_file: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    @router.delete("/files", response_model=StandardResponse)
    async def remove_files(request: RemoveFilesRequest):
        """Remove multiple files by their IDs."""
        try:
            res = await claim_manager_controller.remove_files(request.file_ids)
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to remove some or all files"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": f"Successfully deleted {len(request.file_ids)} files"}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in remove_files: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    return router