from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from app.service.insight_service import InsightService

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
        




    return router

