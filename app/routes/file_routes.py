from fastapi import APIRouter, UploadFile, File, Form, Path
from fastapi.responses import JSONResponse
from app.service.file_service import FileService
from app.models.request_models import FileActionItem
from typing import List
import json
import logging

logger = logging.getLogger(__name__)
file_service = FileService()

def create_file_routes_v2() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/file",
        tags=["Files"]
    )
    
    @router.post("/dupcheck")
    async def check_duplicate_files(
        tenant_id: str = Form(..., description="Tenant ID"),
        case_id: str = Form(..., description="Case ID"),
        files: List[UploadFile] = File(..., description="Files to check for duplicates")
    ):
        """Check for duplicate files before uploading."""
        try:
            res = await file_service.check_duplicate_files(tenant_id, case_id, files)
            
            if not res.get("success", False):
                return JSONResponse(
                    {"success": False, "error": "Duplicate check failed"}, 
                    status_code=500
                )

            return JSONResponse(res, status_code=200)

        except Exception as e:
            logger.error(f"Error in check_duplicate_files: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e)}, 
                status_code=500
            )

    @router.post("/upload")
    async def upload_files(
        tenant_id: str = Form(..., description="Tenant ID"),
        case_id: str = Form(..., description="Case ID"),
        files: List[UploadFile] = File(..., description="Files to upload"),
        file_actions: str = Form(..., description="JSON string of file actions")
    ):
        """Upload files to a case with specified actions."""
        try:
            # Parse and validate file actions
            try:
                actions_data = json.loads(file_actions)
                # Validate each action item
                validated_actions = [FileActionItem(**action) for action in actions_data]
            except (json.JSONDecodeError, ValueError) as e:
                return JSONResponse(
                    {"success": False, "error": f"Invalid file_actions format: {str(e)}"}, 
                    status_code=400
                )
            
            # Validate that number of files matches number of actions
            if len(files) != len(validated_actions):
                return JSONResponse(
                    {"success": False, "error": "Number of files must match number of file actions"}, 
                    status_code=400
                )
            
            # Convert back to dict format for service
            actions_dict = [action.dict() for action in validated_actions]
            
            res = await file_service.upload_files(tenant_id, case_id, files, actions_dict)
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "File upload failed"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "uploaded_files": len(files)}, 
                status_code=201
            )

        except Exception as e:
            logger.error(f"Error in upload_files: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e)}, 
                status_code=500
            )

    return router