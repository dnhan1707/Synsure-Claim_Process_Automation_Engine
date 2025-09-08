from app.service.tenant_service import TenantService
from typing import List, Dict, Any

class TenantController():
    def __init__(self):
        self.tenant_service = TenantService()

    async def create_new_tenant(self, name: str) -> bool:
        try:
            res = await self.tenant_service.insert_new_tenant(name)
            return res

        except Exception as e:
            print("Tenant Controller Error - create_new_tenant", e)
            return False


    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        try:
            res = await self.tenant_service.get_all_tenants()
            return res

        except Exception as e:
            print("Tenant Controller Error - get_all_tenants", e)
            return False
        
    
    async def get_tenant(self, id: str) -> Dict[str, Any]:
        try:
            res = await self.tenant_service.get_tenant(id)
            return res

        except Exception as e:
            print("Tenant Controller Error - get_tenant", e)
            return {}
