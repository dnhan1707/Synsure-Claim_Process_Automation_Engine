from fastapi import APIRouter, Path, HTTPException
from fastapi.responses import JSONResponse
from app.controller.tenant_controller import TenantController
from app.models.request_models import (
    TenantCreationRequest, TenantResponse, TenantsListResponse, StandardResponse
)
import logging

logger = logging.getLogger(__name__)
tenant_controller = TenantController()

def create_tenant_routes() -> APIRouter:
    router = APIRouter(
        prefix="/tenant",
        tags=["Tenants"],
    )
    
    @router.post("/", response_model=StandardResponse)
    async def create_new_tenant(request: TenantCreationRequest):
        """Create a new tenant."""
        try:
            res = await tenant_controller.create_new_tenant(name=request.tenant_name)
            
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to create tenant"}, 
                    status_code=500
                )

            return JSONResponse(
                {"success": True, "message": "Tenant created successfully"}, 
                status_code=201
            )
            
        except Exception as e:
            logger.error(f"Error in create_new_tenant: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )

    @router.get("/", response_model=TenantsListResponse)
    async def get_all_tenants():
        """Get all tenants in the system."""
        try:
            res = await tenant_controller.get_all_tenants()
            
            if not res:
                return JSONResponse(
                    {"success": False, "result": [], "error": "No tenants found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Error in get_all_tenants: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "result": [], "error": "Internal server error"}, 
                status_code=500
            )

    @router.get("/{tenant_id}", response_model=TenantResponse)
    async def get_tenant(
        tenant_id: str = Path(..., description="Tenant ID to retrieve")
    ):
        """Get detailed information about a specific tenant."""
        try:
            res = await tenant_controller.get_tenant(id=tenant_id)
            
            if not res:
                return JSONResponse(
                    {"success": False, "result": {}, "error": "Tenant not found"}, 
                    status_code=404
                )

            return JSONResponse(
                {"success": True, "result": res}, 
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Error in get_tenant: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "result": {}, "error": "Internal server error"}, 
                status_code=500
            )

    return router