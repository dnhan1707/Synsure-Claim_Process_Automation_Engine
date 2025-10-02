from fastapi import APIRouter, UploadFile, File, Form, Path, HTTPException
from fastapi.responses import JSONResponse
from app.service.case_service_v2 import CaseService
from app.models.request_models import StandardResponse
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
case_service = CaseService()

def create_case_routes_v2() -> APIRouter:
    router = APIRouter(
        prefix="/api/v2/case",
        tags=["Cases"]
    )

    @router.post("/")
    async def create_new_case(
        tenant_id: str = Form(..., description="Tenant ID"),
        case_name: str = Form(..., description="Case name"),
        case_type: str = Form(..., description="Case type"),
        files: Optional[List[UploadFile]] = File(None, description="Optional files to upload")
    ):
        """Create a new case with optional file uploads."""
        try:
            new_case_id, saved_files_id = await case_service.create_new_case(
                tenant_id, case_name, case_type, files, status="open", short_des=""
            )

            if not new_case_id:
                return JSONResponse(
                    {"success": False, "new_case_id": "", "error": "Failed to create case"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "new_case_id": new_case_id, "saved_files_count": len(saved_files_id) if saved_files_id else 0}, 
                status_code=201
            )

        except Exception as e:
            logger.error(f"Error in create_new_case: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "new_case_id": ""}, 
                status_code=500
            )

    @router.get("/analytics/most-type")
    async def get_most_case_type_general():
        try:
            res = await case_service.get_most_case_type_general()
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_most_case_type_general"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.get("/analytics/most-type/{tenant_id}")
    async def get_most_case_type_by_tenant(
        tenant_id: str = Path(..., description="Tenant ID"),                                 
    ):
        try:
            res = await case_service.get_most_case_type_by_tenant(tenant_id)
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_most_case_type_by_tenant"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.get("/latestresponse/{tenant_id}/{case_id}")
    async def get_latest_response(
        tenant_id: str = Path(..., description="Tenant ID"),
        case_id: str = Path(..., description="Case ID")
    ):
        """Get the latest AI model response for a case."""
        try:
            res = await case_service.get_latest_response(tenant_id, case_id)

            if not res:
                return JSONResponse(
                    {"success": False, "result": {}, "error": "No response found for this case"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in get_latest_response: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "result": {}}, 
                status_code=500
            )

    @router.get("/{tenant_id}")
    async def get_all_cases(
        tenant_id: str = Path(..., description="Tenant ID")
    ):
        """Get all cases for a tenant."""
        try:
            res = await case_service.get_all_cases_by_tenant(tenant_id)

            if not res:
                return JSONResponse(
                    {"success": False, "result": [], "error": "No cases found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in get_all_cases: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "result": []}, 
                status_code=500
            )

    @router.get("/{tenant_id}/{case_id}")
    async def get_case(
        tenant_id: str = Path(..., description="Tenant ID"),
        case_id: str = Path(..., description="Case ID")
    ):
        """Get detailed information about a specific case."""
        try:
            res = await case_service.get_case(tenant_id, case_id)

            if not res:
                return JSONResponse(
                    {"success": False, "result": {}, "error": "Case not found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            logger.error(f"Error in get_case: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": str(e), "result": {}}, 
                status_code=500
            )

    @router.delete("/{tenant_id}/{case_id}")
    async def delete_case(
        tenant_id: str = Path(..., description="Tenant ID"),
        case_id: str = Path(..., description="Case ID")
    ):
        """
        Delete a case and all its related data.
        
        This will soft delete:
        - The case record
        - All associated files 
        - All responses
        - All tasks
        - All response input files
        - Delete actual files from S3 storage
        
        Returns success status and deletion details.
        """
        try:
            logger.info(f"Delete case request for tenant {tenant_id}, case {case_id}")
            
            # Check if case exists first
            case_exists = await case_service.sp_service.get_case(
                table_name="cases",
                columns="id, case_name",
                tenant_id=tenant_id,
                case_id=case_id
            )
            
            if not case_exists:
                return JSONResponse(
                    {
                        "success": False, 
                        "error": "Case not found or already deleted",
                        "details": {}
                    }, 
                    status_code=404
                )
            
            # Perform the deletion
            result = await case_service.delete_case(tenant_id, case_id)
            
            if result["success"]:
                return JSONResponse(
                    {
                        "success": True,
                        "message": result["message"],
                        "details": result["details"]
                    },
                    status_code=200
                )
            else:
                return JSONResponse(
                    {
                        "success": False,
                        "error": result["error"],
                        "details": result.get("details", {})
                    },
                    status_code=500
                )
                
        except Exception as e:
            logger.error(f"Error in delete_case route: {e}", exc_info=True)
            return JSONResponse(
                {
                    "success": False, 
                    "error": str(e),
                    "details": {}
                }, 
                status_code=500
            )

    return router
