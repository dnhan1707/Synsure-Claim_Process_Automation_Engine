from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.service.case_service_v2 import CaseService
from app.service.submission_service import SubmissionService
from app.models.request_models import SubmitFilesRequest, BatchSubmissionRequest, CaseResponse, SubmissionResponse, BatchResponse
import logging

logger = logging.getLogger(__name__)
case_service = CaseService()
submission_service = SubmissionService()

def create_submission_routes2() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/submission",
        tags=["AI Processing"]    
    )

    @router.post("/newcase", response_model=CaseResponse)
    async def submit_new_case(
        tenant_id: str = Form(..., description="Tenant ID"),
        case_name: str = Form(..., description="Case name"),
        files: list[UploadFile] = File(..., description="Files to upload"),
    ):
        """Create a new case and run with uploaded files."""
        try:
            new_case_id, model_response = await submission_service.submit_new_case(
                tenant_id, case_name, files
            )

            if not new_case_id or not model_response:
                return JSONResponse(
                    {"success": False, "new_case_id": "", "result": {}, "error": "Failed to create case or process files"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "new_case_id": new_case_id, "result": model_response}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in submit_new_case: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "new_case_id": "", "result": {}}, 
                status_code=500
            )

    @router.post("/start", response_model=SubmissionResponse)
    async def submit_with_chosen_files(request: SubmitFilesRequest):
        """Run processing with chosen files from an existing case."""
        try:
            model_response = await submission_service.submit_with_chosen_files(
                request.tenant_id, request.case_id, request.chosen_files
            )
            
            if not model_response or model_response == {}:
                return JSONResponse(
                    {"success": False, "error": "No content generated", "result": {}}, 
                    status_code=500
                )
                
            return JSONResponse(
                {"success": True, "result": model_response}, 
                status_code=200
            ) 

        except Exception as e:
            logger.error(f"Error in submit_with_chosen_files: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "result": {}}, 
                status_code=500
            )
    
    @router.post("/submit-batch-async", response_model=BatchResponse)
    async def submit_batch_async(request: BatchSubmissionRequest):
        """Asynchronous batch processing - returns immediately with task IDs."""
        try:
            logger.info(f"Starting batch processing for tenant {request.tenant_id} with cases {request.case_ids}")
            
            result = await submission_service.submit_many_async(request.tenant_id, request.case_ids)
            
            logger.info(f"Batch processing result: {result}")
            return JSONResponse(result, status_code=200)
            
        except Exception as e:
            logger.error(f"Error in submit_batch_async: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e)}, 
                status_code=500
            )
        
    return router