import logging
from app.service.tenant_service import TenantService
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TenantController():
    def __init__(self):
        self.tenant_service = TenantService()

    async def create_new_tenant(self, name: str) -> bool:
        try:
            res = await self.tenant_service.insert_new_tenant(name)
            return res

        except Exception as e:
            logger.error("Tenant Controller Error - create_new_tenant for name: %s - %s", name, str(e), exc_info=True)
            return False

    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        try:
            res = await self.tenant_service.get_all_tenants()
            return res

        except Exception as e:
            logger.error("Tenant Controller Error - get_all_tenants - %s", str(e), exc_info=True)
            return []
        
    async def get_tenant(self, id: str) -> Dict[str, Any]:
        try:
            res = await self.tenant_service.get_tenant(id)
            return res

        except Exception as e:
            logger.error("Tenant Controller Error - get_tenant for id: %s - %s", id, str(e), exc_info=True)
            return {}