from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schema.schema import TenantCreationRequest
from app.controller.tenant_controller import TenantController


tenant_controller = TenantController()

def create_tenant_routes() -> APIRouter:
    router = APIRouter(
        prefix="/tenant"
    )
    
    @router.post("/")
    async def create_new_tenant(tenant_info: TenantCreationRequest):
        try:
            
            res = await tenant_controller.create_new_tenant(name=tenant_info.tanant_name)
            if not res:
                return JSONResponse({"success": False, "error": "create_new_tenant"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    @router.get("/")
    async def get_all_tenants():
        try:
            res = await tenant_controller.get_all_tenants()
            if not res:
                return JSONResponse({"success": False, "result": [], "error": "get_all_tenants"}, status_code=500) 

            return JSONResponse({"success": True, "result": res}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "result": [], "error": e}, status_code=500) 


    @router.get("/{id}")
    async def get_tenant(id: str):
        try:
            res = await tenant_controller.get_tenant(id=id)
            if not res:
                return JSONResponse({"success": False, "result": {}, "error": "get_tenant"}, status_code=500) 

            return JSONResponse({"success": True, "result": res}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "result": {}, "error": e}, status_code=500) 


    return router
