from fastapi import APIRouter, Security
from fastapi.responses import JSONResponse
from app.service.dashboard_service import DashboardService
from app.routes.auth_routes import get_current_user

import logging


logger = logging.getLogger(__name__)
dashboard_service = DashboardService()

def create_dashboard_route() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/dashboard",
        tags=["Dashboard"],
        dependencies=[Security(get_current_user)]
    )


    @router.get("/not_processed_cases")
    async def number_of_claim_not_processed():
        try:
            res = await dashboard_service.get_cases_not_processed()
            if not res:
                return JSONResponse({"success": False, "result": {}, "error": "Something wrong with get_cases_not_processed"}, status_code=500)

            return JSONResponse({"success": True, "result": res}, status_code=200)


        except Exception as e:
            logger.error("Error in route /not_processed_cases")
            return []
    


    return router

