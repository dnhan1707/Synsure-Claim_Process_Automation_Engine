from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse
from app.service.insight_service import InsightService
from typing import Optional

insight_service = InsightService()

def create_insight_route() -> APIRouter:
    router = APIRouter(
        prefix="/api/v2/insight",
        tags=["Insights"]
    )

    @router.get("/most-type")
    async def get_most_case_type_general():
        try:
            res = await insight_service.get_most_case_type_general()
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_most_case_type_general"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.get("/most-type/{tenant_id}")
    async def get_most_case_type_by_tenant(
        tenant_id: str = Path(..., description="Tenant ID"),                                 
    ):
        try:
            res = await insight_service.get_most_case_type_by_tenant(tenant_id)
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_most_case_type_by_tenant"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        
    
    @router.get("/all-type")
    async def get_all_type_general():
        try:
            res = await insight_service.get_all_type_general()
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_all_type_general"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        

    @router.get("/all-type/{tenant_id}")
    async def get_all_type_by_tenant(
        tenant_id: str = Path(..., description="Tenant ID")
    ):
        try:
            res = await insight_service.get_all_type_by_tenant(tenant_id)
            if not res or res == "":
                return JSONResponse({"success": False, "error": "Error in get_all_type_general"}, status_code=404)

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        


    @router.get("/")
    async def get_insights_general(
        date: Optional[str] = Query(None, description="Date filter in YYYY-MM-DD format"),
        tenant_id: Optional[str] = Query(None, description="Tenant ID filter")
    ):
        """
        Get comprehensive insights with optional filtering.
        
        Query Parameters:
        - date: Optional date filter (YYYY-MM-DD) - shows data for that specific day
        - tenant_id: Optional tenant filter - shows data for specific tenant only
        
        Examples:
        - GET /api/v2/insight/insights  (all data, no filters)
        - GET /api/v2/insight/insights?date=2025-01-15  (data for specific date)
        - GET /api/v2/insight/insights?tenant_id=tenant-123  (data for specific tenant)
        - GET /api/v2/insight/insights?date=2025-01-15&tenant_id=tenant-123  (both filters)
        """

        try:
            res = await insight_service.get_insights(date=date, tenant_id=tenant_id)
            
            if "error" in res:
                return JSONResponse(
                    {"success": False, "error": res["error"], "result": {}}, 
                    status_code=400
                )
            
            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )

        except Exception as e:
            return JSONResponse(
                {"success": False, "error": str(e), "result": {}}, 
                status_code=500
            )


    return router

